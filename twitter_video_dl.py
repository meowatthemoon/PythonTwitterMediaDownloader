#!/usr/bin/env python

import requests as requests
import json
import urllib.parse
import m3u8
from pathlib import Path
import re
import ffmpeg
import shutil

# CODE ADAPTED FROM https://github.com/h4ckninja/twitter-video-downloader full credit to him

video_player_prefix = 'https://twitter.com/i/videos/tweet/'
video_api = 'https://api.twitter.com/1.1/videos/tweet/config/'


def download(url, output_dir):
    tweet_url = url.split('?', 1)[0]
    id = tweet_url.split('/')[5]

    output_path = Path(output_dir)
    storage_dir = output_path
    Path.mkdir(storage_dir, parents=True, exist_ok=True)
    storage = str(storage_dir)

    s_requests = requests.Session()

    token = __get_bearer_token(id, s_requests)

    video_host, playlist = __get_playlist(s_requests, id, token)
    if not playlist.is_variant:
        print("Error")
        return
    plist = playlist.playlists[-1]
    resolution = str(plist.stream_info.resolution[0]) + 'x' + str(plist.stream_info.resolution[1])
    resolution_file = Path(storage) / Path(id + '.mp4')

    playlist_url = video_host + plist.uri

    ts_m3u8_response = s_requests.get(playlist_url, headers={'Authorization': None})
    ts_m3u8_parse = m3u8.loads(ts_m3u8_response.text)

    ts_list = []
    ts_full_file_list = []

    for ts_uri in ts_m3u8_parse.segments.uri:
        # ts_list.append(video_host + ts_uri)

        ts_file = requests.get(video_host + ts_uri)
        fname = ts_uri.split('/')[-1]
        ts_path = Path(storage) / Path(fname)
        ts_list.append(ts_path)

        ts_path.write_bytes(ts_file.content)

    ts_full_file = Path(storage) / Path(resolution + '.ts')
    ts_full_file = str(ts_full_file)
    ts_full_file_list.append(ts_full_file)

    # Shamelessly taken from https://stackoverflow.com/questions/13613336/python-concatenate-text-files/27077437#27077437
    with open(str(ts_full_file), 'wb') as wfd:
        for f in ts_list:
            with open(f, 'rb') as fd:
                shutil.copyfileobj(fd, wfd, 1024 * 1024 * 10)

    for ts in ts_full_file_list:
        ffmpeg \
            .input(ts) \
            .output(str(resolution_file), acodec='copy', vcodec='libx264', format='mp4', loglevel='error') \
            .overwrite_output() \
            .run()

    for ts in ts_list:
        p = Path(ts)
        p.unlink()

    for ts in ts_full_file_list:
        p = Path(ts)
        p.unlink()


def __get_bearer_token(id, s_requests):
    video_player_url = video_player_prefix + id
    video_player_response = s_requests.get(video_player_url).text

    js_file_url = re.findall('src="(.*js)', video_player_response)[0]
    js_file_response = s_requests.get(js_file_url).text

    bearer_token_pattern = re.compile('Bearer ([a-zA-Z0-9%-])+')
    bearer_token = bearer_token_pattern.search(js_file_response)
    bearer_token = bearer_token.group(0)
    s_requests.headers.update({'Authorization': bearer_token})

    return bearer_token


def __get_playlist(s_requests, id, token):
    player_config_req = s_requests.get(video_api + id + '.json')

    player_config = json.loads(player_config_req.text)

    if 'errors' not in player_config:
        m3u8_url = player_config['track']['playbackUrl']

    else:
        print('[-] Rate limit exceeded. Could not recover. Try again later.')
        exit(1)

    # Get m3u8
    m3u8_response = s_requests.get(m3u8_url)

    m3u8_url_parse = urllib.parse.urlparse(m3u8_url)
    video_host = m3u8_url_parse.scheme + '://' + m3u8_url_parse.hostname

    m3u8_parse = m3u8.loads(m3u8_response.text)

    return [video_host, m3u8_parse]


if __name__ == '__main__':
    download("https://twitter.com/i/status/1294436502181539840", "./videos")

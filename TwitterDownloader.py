import tweepy
from tweepy import OAuthHandler
import json
import wget
import os
import twitter_video_dl

# Based on https://miguelmalvarez.com/2015/03/03/download-the-pictures-from-a-twitter-feed-using-python/

consumer_key = 'YOUR_TWITTER_CONSUMER_KEY'
consumer_secret = 'YOUR_TWITTER_CONSUMER_SECRET'
access_token = 'YOUR_TWITTER_ACCESS_TOKEN'
access_secret = 'YOUR_TWITTER_ACCESS_SECRET'


@classmethod
def parse(cls, api, raw):
    status = cls.first_parse(api, raw)
    setattr(status, 'json', json.dumps(raw))
    return status


def get_images_videos(username, img_dir, video_dir, include_rts=True, exclude_replies=False):
    if not os.path.isdir(img_dir):
        os.mkdir(img_dir)
    if not os.path.isdir(video_dir):
        os.mkdir(video_dir)

    tweepy.models.Status.first_parse = tweepy.models.Status.parse
    tweepy.models.Status.parse = parse

    tweepy.models.User.first_parse = tweepy.models.User.parse
    tweepy.models.User.parse = parse

    auth = OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_secret)

    api = tweepy.API(auth)

    tweets = api.user_timeline(screen_name=username,
                               count=200, include_rts=include_rts,
                               exclude_replies=exclude_replies)
    last_id = tweets[-1].id

    while True:
        more_tweets = api.user_timeline(screen_name=username,
                                        count=200,
                                        include_rts=include_rts,
                                        exclude_replies=exclude_replies,
                                        max_id=last_id - 1)
        if len(more_tweets) == 0:
            break
        else:
            last_id = more_tweets[-1].id - 1
            tweets = tweets + more_tweets

    print(f"Found {len(tweets)} tweets")

    media_files = set()
    for status in tweets:
        media = status.entities.get('media', [])
        if len(media) > 0:
            if "ext_tw_video" in media[0]['media_url']:  # video
                media_files.add(media[0]['expanded_url'])
            else:  # image
                media_files.add(media[0]['media_url'])

    for index, media_file in enumerate(media_files):
        if "/video/" in media_file:
            twitter_video_dl.download(media_file, video_dir)
        else:
            wget.download(media_file, out=img_dir + str(index) + ".jpg")


get_images_videos("elonmusk", "imgs", "videos")

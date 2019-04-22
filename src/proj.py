#!/usr/bin/env python
import argparse
import json
import os.path
import psaw
import praw
import requests
import time
import toml

# source: https://old.reddit.com/r/datasets/comments/9zhj46/how_to_get_an_archive_of_all_your_comments_from/
def get_comments_from_pushshift(**kwargs):
    r = requests.get("https://api.pushshift.io/reddit/comment/search/",params=kwargs)
    data = r.json()
    return data['data']
# source: https://old.reddit.com/r/datasets/comments/9zhj46/how_to_get_an_archive_of_all_your_comments_from/
def get_comments_from_reddit_api(comment_ids):
    headers = {'User-agent':'Comment Collector'}
    params = {}
    params['id'] = ','.join(["t1_" + id for id in comment_ids])
    r = requests.get("https://api.reddit.com/api/info",params=params,headers=headers)
    data = r.json()
    return data['data']['children']
# source: https://old.reddit.com/r/datasets/comments/9zhj46/how_to_get_an_archive_of_all_your_comments_from/
def get_comments(author):
    before = None
    while True:
        comments = get_comments_from_pushshift(author=author,size=100,before=before,sort='desc',sort_type='created_utc')
        if not comments: break

        # This will get the comment ids from Pushshift in batches of 100 -- Reddit's API only allows 100 at a time
        comment_ids = []
        for comment in comments:
            before = comment['created_utc'] # This will keep track of your position for the next call in the while loop
            comment_ids.append(comment['id'])

        # This will then pass the ids collected from Pushshift and query Reddit's API for the most up to date information
        comments = get_comments_from_reddit_api(comment_ids)
        for comment in comments:
            comment = comment['data']
            # Do stuff with the comments
            print(comment['score'],comment['subreddit'],comment['author'])

        time.sleep(2) # I'm not sure how often you can query the Reddit API without oauth but once every two seconds should work fine
    return comments

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-c',
        '--config',
        default='config.toml',
        help='Path to TOML configuration file')
    parser.add_argument('gather', help='Gather data')
    args = parser.parse_args()

    cfg = toml.load(args.config)
    reddit = praw.Reddit(
        client_id=cfg['bot'][0]['client_id'],
        client_secret=cfg['bot'][0]['client_secret'],
        password=cfg['bot'][0]['password'],
        user_agent=cfg['bot'][0]['user_agent'],
        username=cfg['bot'][0]['username'])

    ps = psaw.PushshiftAPI(reddit)

    subreddit = 'privacy'
    threshold = 10

    # get relevant posts in the subreddit
    gen = ps.search_submissions(
        limit=100, subreddit=subreddit, before='25d', sort_type='score')
    results = list(gen)

    users = []
    for r in results:
        print('author: {}, submission: {}'.format(r.author, r.title))
        for c in r.comments:
            u = c.author
            if u in users or u is None:
                continue
            users.append(u)
            print('comment author: {}'.format(u))
        break

    # get statistics for each user
    userstats = {}
    for u in users:
        fname = "data/" + u.name + ".json"
        if os.path.isfile(fname):
            continue
        with open(fname, "w") as f:
            result = ps.redditor_subreddit_activity(u)
            userstats['activity'] = result
            print(result)
            # get stats for each comment
            commentstats = []
            for comment in get_comments(u.name):
                print("comment {}, score {}, subreddit {}, timestamp {}".format(
                    comment, comment.score, comment.subreddit.display_name, comment.created_utc))
                commentstats.append({
                    "score": comment.score,
                    "subreddit": comment.subreddit.display_name,
                    "subreddit_id": comment.subreddit.name,
                    "time": comment.created_utc,
                    "subtime": comment.submission.created_utc,
                    "subnumcomments": comment.submission.num_comments,
                    "subscore": comment.submission.score
                })
            result['commentstats'] = commentstats
            json.dump(result, f)

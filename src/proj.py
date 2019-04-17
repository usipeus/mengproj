#!/usr/bin/env python
import argparse
import psaw
import praw
import toml

from time import sleep

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
    stats = {}
    for u in users:
        result = ps.redditor_subreddit_activity(u)
        print(result)
        # get stats for each comment
        for comment in u.comments.new(limit=None):
            print("comment {}, score{}, body {}, subreddit {}, timestamp {}".format(
                comment, comment.score, comment.body, comment.subreddit, comment.created_utc))
            break
        stats[u] = result
        break
        sleep(1)

    print(stats)

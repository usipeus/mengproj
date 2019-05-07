#!/usr/bin/env python
import altair as alt
import argparse
import json
import psaw
import praw
import requests
import time
import toml

from os import listdir
from os.path import isfile, join


# source: https://old.reddit.com/r/datasets/comments/9zhj46/how_to_get_an_archive_of_all_your_comments_from/
def get_comments_from_pushshift(**kwargs):
    r = requests.get(
        "https://api.pushshift.io/reddit/comment/search/", params=kwargs)
    data = r.json()
    return data['data']


# source: https://old.reddit.com/r/datasets/comments/9zhj46/how_to_get_an_archive_of_all_your_comments_from/
def get_comments_from_reddit_api(comment_ids):
    headers = {'User-agent': 'Comment Collector'}
    params = {}
    params['id'] = ','.join(["t1_" + id for id in comment_ids])
    r = requests.get(
        "https://api.reddit.com/api/info", params=params, headers=headers)
    data = r.json()
    return data['data']['children']


# source: https://old.reddit.com/r/datasets/comments/9zhj46/how_to_get_an_archive_of_all_your_comments_from/
def get_comments(author):
    before = None
    while True:
        comments = get_comments_from_pushshift(
            author=author,
            size=100,
            before=before,
            sort='desc',
            sort_type='created_utc')
        if not comments: break

        # This will get the comment ids from Pushshift in batches of 100 -- Reddit's API only allows 100 at a time
        comment_ids = []
        for comment in comments:
            before = comment[
                'created_utc']  # This will keep track of your position for the next call in the while loop
            comment_ids.append(comment['id'])

        # This will then pass the ids collected from Pushshift and query Reddit's API for the most up to date information
        comments = get_comments_from_reddit_api(comment_ids)
        for comment in comments:
            comment = comment['data']
            # Do stuff with the comments
            #print(comment['score'], comment['subreddit'], comment['author'])

        time.sleep(
            2
        )  # I'm not sure how often you can query the Reddit API without oauth but once every two seconds should work fine
    return comments


def get_top_user_stats(reddit,
                       ps,
                       before=None,
                       limit=None,
                       sort_type=None,
                       subreddit=None):
    # get relevant posts in the subreddit
    print("Getting submissions:")
    gen = ps.search_submissions(
        limit=limit, subreddit=subreddit, before=before, sort_type=sort_type)
    results = list(gen)

    users = []
    for r in results:
        print('author: {}, submission: {}'.format(r.author, r.title))
        for c in r.comments:
            u = None
            if isinstance(c, praw.models.MoreComments):
                continue
            u = c.author
            if u in users or u is None:
                continue
            users.append(u)
            print('comment author: {}'.format(u))

    # get statistics for each user
    userstats = {}
    for u in users:
        fname = "./data/" + subreddit + "/" + u.name + ".json"
        if isfile(fname):
            continue
        with open(fname, "w") as f:
            result = ps.redditor_subreddit_activity(u)
            userstats['activity'] = result
            print(result)
            # get stats for each comment
            commentstats = []
            for comment in get_comments(u.name):
                print(
                    "comment {}, score {}, subreddit {}, timestamp {}".format(
                        comment, comment.score, comment.subreddit.display_name,
                        comment.created_utc))
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


def gen_viz(path):
    stats = {}
    fnames = [f for f in listdir(path) if isfile(join(path, f))]
    for f in fnames:
        try:
            print(f)
            fp = open(path + f, "r")
            data = json.load(fp)
        except Exception:
            continue

        comment_ratio = {}
        submission_ratio = {}
        cur_sum = 0
        for k, n in data["comment"].items():
            cur_sum += n
        for k, n in data["comment"].items():
            comment_ratio[k] = n / cur_sum

        cur_sum = 0
        for k, n in data["submission"].items():
            cur_sum += n
        for k, n in data["submission"].items():
            submission_ratio[k] = n / cur_sum

        user = f[:-5]
        stats[user] = {}
        stats[user]["comment_ratio"] = comment_ratio
        stats[user]["submission_ratio"] = submission_ratio

    comment_ratios = []
    for k, v in stats.items():
        print(v)
        if "privacy" in v["comment_ratio"].keys():
            comment_ratios.append(v["comment_ratio"]["privacy"])
    print(comment_ratios)

    chart = alt.Chart(comment_ratios).mark_bar().encode(
        alt.X("ratio of comments in /r/privacy to total comments (binned)", bin=alt.BinParams(maxbins=100)),
        y="count(*):Q"
    )
    chart.save("testchart.html")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='proj.py')
    subparsers = parser.add_subparsers(
        required=True, dest='subparser', help='sub-command help')

    gather = subparsers.add_parser('gather', help='Gather data')
    viz = subparsers.add_parser('viz', help='Generate visualizations')

    # arguments for gather subcommand
    gather.add_argument(
        '-r',
        '--subreddit',
        default='privacy',
        help='Subreddit to pull data from')
    gather.add_argument(
        '--before', default='30d', help='Time before now to get data from')
    gather.add_argument(
        '-c',
        '--config',
        default='config.toml',
        help='Path to TOML configuration file')
    gather.add_argument(
        '-l',
        '--limit',
        default='1',
        help='Limit of submissions to pull user stats from')
    gather.add_argument(
        '--sort_type',
        default='score',
        help='Sort type of the submissions, see https://pypi.org/project/psaw/'
    )

    # arguments for viz subcommand
    viz.add_argument(
        '-p',
        '--path',
        required=True,
        help=
        'Path to generate visualizations from .json files, e.g. data/privacy')

    args = parser.parse_args()
    print(args)

    if args.subparser == 'gather':
        cfg = toml.load(args.config)
        reddit = praw.Reddit(
            client_id=cfg['bot'][0]['client_id'],
            client_secret=cfg['bot'][0]['client_secret'],
            password=cfg['bot'][0]['password'],
            user_agent=cfg['bot'][0]['user_agent'],
            username=cfg['bot'][0]['username'])

        ps = psaw.PushshiftAPI(reddit)
        get_top_user_stats(
            reddit,
            ps,
            before=args.before,
            limit=int(args.limit),
            sort_type=args.sort_type,
            subreddit=args.subreddit)

    if args.subparser == 'viz':
        gen_viz(args.path)

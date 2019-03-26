import argparse
import psaw
import praw
import toml

from time import sleep


def is_reddit_bot(author):
    return author.name.lower().startswith('auto')


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

    gen = ps.search_submissions(
        limit=100, subreddit=subreddit, before='25d', sort_type='score')
    results = list(gen)

    seen_users = []
    users = []
    for r in results:
        print('author: {}, submission: {}'.format(r.author, r.title))
        for c in r.comments:
            print('comment author: {}'.format(c.author))
            u = c.author
            if u in seen_users:
                continue
            agg = ps.search_comments(author=u, aggs='subreddit')
            agg = next(agg)
            for a in agg:
                if a['key'] == subreddit and a['doc_count'] >= threshold:
                    users.append(u)
            seen_users.append(u)
            sleep(2)
            break
        break

    print(users)

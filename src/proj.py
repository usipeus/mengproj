import argparse
import praw
import toml

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-c',
        '--config',
        default='config.toml',
        help='Path to TOML configuration file')
    args = parser.parse_args()

    cfg = toml.load(args.config)
    print(cfg)
    reddit = praw.Reddit(
        client_id=cfg['bot'][0]['client_id'],
        client_secret=cfg['bot'][0]['client_secret'],
        password=cfg['bot'][0]['password'],
        user_agent=cfg['bot'][0]['user_agent'],
        username=cfg['bot'][0]['username'])
    for submission in reddit.front.hot(limit=8):
        print(submission.score)

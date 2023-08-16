"""tweet_rehydrater.py
Rehydrates tweets from the Twitter API for a filename of tweet ids
Uses the full archive search endpoint

@author Gina Sprint
@date 6/15/23
"""

import os
import argparse
import pandas as pd

from utils import TWEET_FIELDS, EXPANSIONS,\
    setup_logging, log_response_errors, setup_twitter_client, build_tweet_ser

# setup logging since running can take several hours due to API rate limits
LOG_FNAME = "rehydrater.log"
logger = setup_logging(LOG_FNAME)

# setup twitter client
client = setup_twitter_client()

# directory to load tweets needing rehydrating from
CONGRESS_TWEET_IDS_DIRNAME = "congress_tweet_ids"
# directory to store fetched tweets
REHYDRATED_TWEET_DIRNAME = "rehydrated_tweet_data"

def lookup_tweets(tweet_list):
    """Makes a request to twitter API for tweets by id.

    Args:
        tweet_list (list of int): list of tweet IDs to rehydrate

    Returns:
        tweet_list (list of pd.Series): the tweets returned from the API
            each tweet is stored as a Series with only the relevant fields needed for graph making

    Notes:
        https://docs.tweepy.org/en/stable/client.html#tweepy.Client.get_tweets
    """
    tweet_list = [str(tweet_id) for tweet_id in tweet_list]
    tweet_list_str = ",".join(tweet_list)
    get_users_tweets_kwargs = {"tweet_fields": TWEET_FIELDS,
                        "expansions": EXPANSIONS}
    response = client.get_tweets(tweet_list_str, **get_users_tweets_kwargs)

    tweet_list = []
    if response.data is not None:
        for tweet in response.data:
            tweet_ser = build_tweet_ser(response, tweet)
            tweet_list.append(tweet_ser)
    else:
        log_response_errors(logger, response.errors)
    return tweet_list

def request_and_write_tweets_for_user_to_file(tweet_list,
                                              rehydrated_tweets_fname):
    """Requests the tweets and writes the returned tweets to file.

    Args:
        tweet_list (list of int): list of tweet IDs to rehydrate
        tweets_fname (str): name of CSV file to write tweets to

    Returns:
        len(tweet_list) (int): the number of tweets returned from the API for this user
    """
    rehydrated_tweet_list = []
    # can only look up 100 per request
    for i in range (0, len(tweet_list), 100):
        end_index = i + 100
        rehydrated_tweet_list += lookup_tweets(tweet_list[i:end_index])
    log_msg = f"\t# of tweets rehydrated: {len(rehydrated_tweet_list)}/{len(tweet_list)}"
    logger.debug(log_msg)
    if len(rehydrated_tweet_list) > 0:
        tweet_df = pd.DataFrame(rehydrated_tweet_list)
        tweet_df = tweet_df.set_index("tweet_id")
        tweet_df.to_csv(rehydrated_tweets_fname)
    return len(rehydrated_tweet_list)

def rehydrate_all_tweets(tweet_fnames,
                         tweet_directory_name,
                         rehydrated_tweet_directory_name):
    """Iterates through each user's file in the input tweets directory and rehydrates the tweets.

    Args:
        tweet_fnames (list of str): list of filenames to process in tweet_directory_name
            directory
        tweet_directory_name (str): name of the directory to read tweets needing rehydrating CSV
            files from rehydrated_tweet_directory_name (str): name of the directory to write tweets
            CSV files to

    Returns:
        total_tweets (int): the number of total tweets returned from the API for all users
    """
    total_tweets = 0
    for i, tweets_fname in enumerate(tweet_fnames):
        user_id = int(tweets_fname.split("_")[0])
        tweets_fname = os.path.join(tweet_directory_name, tweets_fname)
        tweet_list = pd.read_csv(tweets_fname, header=None).squeeze("columns").tolist()
        rehydrated_tweets_fname = os.path.join(rehydrated_tweet_directory_name,
                                               str(user_id) + "_tweets.csv")
        log_msg = f"Currently processing #{i + 1}/{len(tweet_fnames)}:\
                     {tweets_fname} -> {rehydrated_tweets_fname}"
        logger.debug(log_msg)
        total_tweets += request_and_write_tweets_for_user_to_file(tweet_list,
                                                                  rehydrated_tweets_fname)

    return total_tweets

def main(tweet_directory_name,
         rehydrated_tweet_directory_name):
    """Starts the data rehydrated using values from cmd line args or defaults for
        Congressional dataset.

    Args:
        tweet_directory_name (str): name of the directory to read tweets needing
            rehydrating CSV files from
        rehydrated_tweet_directory_name (str): name of the directory to write
            rehydrated tweets CSV files to
    """
    if not os.path.exists(rehydrated_tweet_directory_name):
        os.mkdir(rehydrated_tweet_directory_name)
    fnames = [fname for fname in list(os.listdir(tweet_directory_name))\
              if os.path.splitext(fname)[1] in [".txt", ".csv"]]

    log_msg = f"START OF RUN: rehydrating tweets for {len(fnames)} users"
    logger.debug(log_msg)
    total_tweets = rehydrate_all_tweets(fnames,
                                        tweet_directory_name,
                                        rehydrated_tweet_directory_name)
    log_msg = f"END OF RUN: rehydrated {total_tweets} tweets"
    logger.debug(log_msg)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rehydrate tweets from Twitter API")
    parser.add_argument("-i",
                        type=str,
                        dest="tweet_directory_name",
                        default=CONGRESS_TWEET_IDS_DIRNAME,
                        help="The directory to read the tweet files needing rehydrating from")
    parser.add_argument("-r",
                        type=str,
                        dest="rehydrated_tweet_directory_name",
                        default=REHYDRATED_TWEET_DIRNAME,
                        help="The directory to write the rehydrated tweet CSV files to")

    args = parser.parse_args()
    main(args.tweet_directory_name, args.rehydrated_tweet_directory_name)

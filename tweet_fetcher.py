"""tweet_fectcher.py
Fetches tweets in a date range from the Twitter API for a filename of user ids
Uses the full archive search endpoint

@author Gina Sprint
@date 6/15/23
"""

import os
import argparse
import pandas as pd
import tweepy

from utils import TWEET_FIELDS, EXPANSIONS,\
    setup_logging, log_response_errors, setup_twitter_client, build_tweet_ser
CONGRESS_USER_IDS_FILENAME = "congress_ids.txt"

# setup logging since running can take several hours due to API rate limits
LOG_FNAME = "fetcher.log"
logger = setup_logging(LOG_FNAME)

# setup twitter client
client = setup_twitter_client()

# twitter API endpoint documentation and parameters
# https://developer.twitter.com/en/docs/twitter-api/tweets/search/api-reference/get-tweets-search-all
START_TIMESTAMP = "2022-02-09 22:01:13+00:00"
END_TIMESTAMP = "2022-06-09 00:00:00+00:00"

# directory to store fetched tweets
FETCHED_TWEET_DIRNAME = "fetched_tweet_data"

def full_archive_search_tweets_for_user(user_id,
                                        start_timestamp,
                                        end_timestamp,
                                        per_user_tweet_count_limit=None):
    """Makes a request to twitter API for tweets in a date range.

    Args:
        user_id (int): id for user to fetch tweets from
        start_datetime (pd.Timestamp): date range starting timestamp
        end_datetime (pd.Timestamp): date range ending timestamp
        per_user_tweet_count_limit (int): number of tweets to limit request
            if you want all tweets in the date range, set to None (default)

    Returns:
        tweet_list (list of pd.Series): the tweets returned from the API
            each tweet is stored as a Series with only the relevant fields needed for graph making

    Notes:
        https://docs.tweepy.org/en/stable/client.html#tweepy.Client.search_all_tweets
    """
    max_results = per_user_tweet_count_limit if\
        per_user_tweet_count_limit is not None else 500 # current twitter request max
    get_users_tweets_kwargs = {"max_results": max_results,
                        "start_time": start_timestamp,
                        "end_time": end_timestamp,
                        "tweet_fields": TWEET_FIELDS,
                        "expansions": EXPANSIONS}
    # want all tweets in date range, use tweepy result Paginator
    if per_user_tweet_count_limit is None:
        responses = tweepy.Paginator(client.search_all_tweets,
                "from:" + str(user_id), **get_users_tweets_kwargs)
    # only want per_user_tweet_count_limit tweets in this date range
    else:
        responses = [client.search_all_tweets("from:" + str(user_id), **get_users_tweets_kwargs)]

    tweet_list = []
    for response in responses:
        if response.data is not None:
            for tweet in response.data:
                tweet_ser = build_tweet_ser(response, tweet)
                tweet_list.append(tweet_ser)
        else:
            log_response_errors(logger, response.errors)
    return tweet_list

def request_and_write_tweets_for_user_to_file(user_id,
                                              start_timestamp,
                                              end_timestamp,
                                              tweets_fname,
                                              per_user_tweet_count_limit=None):
    """Requests the tweets and writes the returned tweets to file.

    Args:
        user_id (int): id for user to fetch tweets from
        start_datetime (pd.Timestamp): date range starting timestamp
        end_datetime (pd.Timestamp): date range ending timestamp
        tweets_fname (str): name of CSV file to write tweets to
        per_user_tweet_count_limit (int): number of tweets to limit request
            if you want all tweets in the date range, set to None (default)

    Returns:
        len(tweet_list) (int): the number of tweets returned from the API for this user
    """
    tweet_list = full_archive_search_tweets_for_user(user_id,
                                                     start_timestamp,
                                                     end_timestamp,
                                                     per_user_tweet_count_limit)
    log_msg = f"\t# of tweets fetched: {len(tweet_list)}"
    logger.debug(log_msg)
    if len(tweet_list) > 0:
        tweet_df = pd.DataFrame(tweet_list)
        tweet_df = tweet_df.set_index("tweet_id")
        tweet_df.to_csv(tweets_fname)
    return len(tweet_list)

def process_all_users_tweets(user_ids_ser,
                             tweet_directory_name,
                             start_timestamp,
                             end_timestamp,
                             per_user_tweet_count_limit=None):
    """Iterates through each user in the input file.

    Args:
        user_ids_ser (pd.Series): ids for users to fetch tweets from
        tweet_directory_name (str): name of the directory to write tweets CSV files to
        start_datetime (pd.Timestamp): date range starting timestamp
        end_datetime (pd.Timestamp): date range ending timestamp
        per_user_tweet_count_limit (int): number of tweets to limit request
            if you want all tweets in the date range, set to None (default)

    Returns:
        total_tweets (int): the number of total tweets returned from the API for all users
    """
    total_tweets = 0
    for i, user_id in enumerate(user_ids_ser):
        user_id_tweets_fname = os.path.join(tweet_directory_name, str(user_id) + "_tweets.csv")
        log_msg = f"Currently processing #{i + 1}/{user_ids_ser.shape[0]}: {user_id_tweets_fname}"
        logger.debug(log_msg)
        total_tweets += request_and_write_tweets_for_user_to_file(user_id,
                                                                  start_timestamp,
                                                                  end_timestamp,
                                                                  user_id_tweets_fname,
                                                                  per_user_tweet_count_limit)
    return total_tweets

def main(user_ids_filename,
         tweet_directory_name,
         start_timestamp,
         end_timestamp,
         per_user_tweet_count_limit=None):
    """Starts the data fetcher using values from cmd line args or
        defaults for Congressional dataset.

    Args:
        user_ids_filename (str): name of the file with the Twitter user ids to fetch tweets for
        tweet_directory_name (str): name of the directory to write tweets CSV files to
        start_datetime (pd.Timestamp): date range starting timestamp
        end_datetime (pd.Timestamp): date range ending timestamp
        per_user_tweet_count_limit (int): number of tweets to limit request
            (must be between 10 and 500)
            if you want all tweets in the date range, set to None (default)
    """
    if not os.path.exists(tweet_directory_name):
        os.mkdir(tweet_directory_name)
    start_timestamp = pd.Timestamp(start_timestamp)
    end_timestamp = pd.Timestamp(end_timestamp)

    user_ids_ser = pd.read_csv(user_ids_filename).squeeze("columns")

    log_msg = f"START OF RUN: fetching tweets for {user_ids_ser.shape[0]} users"
    logger.debug(log_msg)
    user_ids_ser = user_ids_ser.iloc[:5]
    # fetch and write relevant tweet info to file for each user in date range
    # per_user_tweet_count_limit must be None (all tweets) or between 10 and 500
    total_tweets = process_all_users_tweets(user_ids_ser,
                                            tweet_directory_name,
                                            start_timestamp,
                                            end_timestamp,
                                            per_user_tweet_count_limit)
    log_msg = f"END OF RUN: fetched {total_tweets} tweets"
    logger.debug(log_msg)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch tweets from Twitter API")
    parser.add_argument("-i",
                        type=str,
                        dest="user_ids_filename",
                        default=CONGRESS_USER_IDS_FILENAME,
                        help="A text file with one twitter user id per line")
    parser.add_argument("-t",
                        type=str,
                        dest="tweet_directory_name",
                        default=FETCHED_TWEET_DIRNAME,
                        help="The name of the directory to write the tweet CSV files to")
    parser.add_argument("-s",
                        type=str,
                        dest="start_timestamp",
                        default=START_TIMESTAMP,
                        help="The starting UTC timestamp (YYYY-MM-DDTHH:mm:ssZ)\
                            for the date range to fetch tweets in")
    parser.add_argument("-e",
                        type=str,
                        dest="end_timestamp",
                        default=END_TIMESTAMP,
                        help="The ending UTC timestamp (YYYY-MM-DDTHH:mm:ssZ)\
                            for the date range to fetch tweets in")
    parser.add_argument("-l",
                        type=int,
                        dest="per_user_tweet_count_limit",
                        default=None,
                        help="A limit on the number of tweets to fetch in the date range.\
                            Must be between 10 and 500.\
                            Omit to default to all tweets in date range.")

    args = parser.parse_args()
    main(args.user_ids_filename,
         args.tweet_directory_name,
         args.start_timestamp,
         args.end_timestamp,
         args.per_user_tweet_count_limit)

"""utils.py
Utility functions for working with Twitter API
Used by tweet_rehydrater.py and tweet_fetcher.py

@author Gina Sprint
@date 6/15/23
"""

import logging
import json
import pandas as pd
import tweepy

# for twitter client setup
KEYS_FNAME = "twitter_keys.json"
WAIT_ON_RATE_LIMIT = True

# twitter API endpoint documentation and parameters
# https://developer.twitter.com/en/docs/twitter-api/fields
TWEET_FIELDS = ["referenced_tweets", "in_reply_to_user_id", "entities"]
# https://developer.twitter.com/en/docs/twitter-api/expansions
EXPANSIONS = ["referenced_tweets.id.author_id"]

def setup_logging(log_fname):
    """Loads bearer token for Twitter API from file and uses it
        to authenticate with Twitter.

    Args:
        log_fname (str): name of the log file to write to.

    Returns:
        logging.Logger: Logger object used to write to the log file.
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s.%(msecs)06f %(message)s', \
                                  datefmt="%Y-%m-%d %H:%M:%S")
    file_handler = logging.FileHandler(log_fname)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    return logger

def log_response_errors(logger,
                        errors):
    """Write any request errors to the log file.

    Args:
        errors (list of dict): a list of error dictionaries
    """
    if len(errors) > 0:
        for i, error in enumerate(errors):
            title = error["title"]
            detail = error["detail"]
            debug_msg = f"Error #{i} {title}: {detail}"
            logger.debug(debug_msg)

def setup_twitter_client():
    """Loads bearer token for Twitter API from file and uses it
        to authenticate with Twitter.

    Returns:
        tweepy.client.Client: Tweepy Client object used for accessing Twitter API.
    """
    with open(KEYS_FNAME) as infile:
        keys_dict = json.load(infile)
        client = tweepy.Client(bearer_token=keys_dict["bearer_token"],
            return_type=tweepy.Response,
            wait_on_rate_limit=WAIT_ON_RATE_LIMIT)
    return client

def find_referenced_tweet_author_ids(tweet,
                                     includes):
    """Processes the referenced tweets for a tweet. These can be of time replied_to,
        retweeted, or quoted.

    Args:
        tweet (tweepy.tweet.Tweet): the tweet object
        includes (dict): the includes object containing user objects for the author
            of referenced tweets

    Returns:
        author_ids_dict (dict): the parsed replied_to, retweeted, and quoted tweet author ids
    """
    replied_to_author_ids = []
    retweeted_author_id = []
    quoted_author_ids = []
    # referenced_tweets is for the current single fetched tweet, whereas includes
    # contains all the referenced tweets for the batch (of possibly 500 tweets)
    referenced_tweets = tweet.referenced_tweets if tweet.referenced_tweets is not None else []
    for referenced_tweet in referenced_tweets:
        # referenced_tweet has a tweet id and a type
        referenced_tweet_type = referenced_tweet["type"]
        referenced_tweet_id = referenced_tweet["id"]
        referenced_tweet_dict = {tweet["id"]: tweet for tweet in includes["tweets"]}
        if referenced_tweet_id in referenced_tweet_dict:
            source_tweet = referenced_tweet_dict[referenced_tweet_id]
            referenced_tweet_author_id = int(source_tweet.author_id)
            if referenced_tweet_type == "replied_to":
                replied_to_author_ids.append(referenced_tweet_author_id)
            if referenced_tweet_type == "retweeted":
                retweeted_author_id.append(referenced_tweet_author_id)
            if referenced_tweet_type == "quoted":
                quoted_author_ids.append(referenced_tweet_author_id)
        elif referenced_tweet["type"] == "replied_to":
            # if the source_tweet was deleted, then can't get its user_id from includes
            # use the in_reply_to_user_id which isn't null'd on tweet delete
            # but can be nulled on user account delete
            replied_to_author_ids.append(tweet.in_reply_to_user_id)

    author_ids_dict = {"replied_to_author_ids": replied_to_author_ids,
                       "retweeted_author_ids": retweeted_author_id,
                       "quoted_author_ids": quoted_author_ids}
    return author_ids_dict

def build_tweet_ser(response,
                    tweet):
    """Creates a Series to represent a tweet.

    Args:
        response (tweepy.client.Response): the API response
        tweet (tweepy.tweet.Tweet): the tweet object

    Returns:
        tweet_ser (pd.Series): a Series with only the relevant tweet fields needed for graph making

    Notes:
        https://docs.tweepy.org/en/stable/response.html
        https://docs.tweepy.org/en/stable/v2_models.html#tweet
    """
    tweet_ser = pd.Series(dtype=str)
    tweet_ser["tweet_id"] = tweet.id
    author_ids_dict = find_referenced_tweet_author_ids(tweet, response.includes)
    for author_id_key, author_id_list in author_ids_dict.items():
        tweet_ser[author_id_key] = str(author_id_list)
    mentioned_user_ids = []
    if tweet.entities is not None and "mentions" in tweet.entities.keys():
        mentioned_user_ids = [int(mention["id"]) for mention in tweet.entities["mentions"]]
    tweet_ser["mentioned_user_ids"] = str(mentioned_user_ids)
    return tweet_ser

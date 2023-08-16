"""graph_maker.py
Makes a weighted, bidirectional graph using tweets fetched
from the Twitter API (see tweet_fetcher.py)

@author Gina Sprint
@date 6/15/23
"""

import os
import argparse
import ast
import pandas as pd
import networkx as nx

from tweet_rehydrater import REHYDRATED_TWEET_DIRNAME
GRAPH_EDGELIST_FILENAME = "network.weighted.edgelist"

def generate_edge_key(src_user_id,
                      dest_user_id):
    """Generate a unique key to identify an edge in a multi edge graph (bidirectional in this case).

    Args:
        src_user_id (int): Twitter user id for the source node in an edge being considered
            (e.g. A in A->B)
        dest_user_id (int): Twitter user id for the destination node in an edge being considered
            (e.g. B in A->B)

    Returns:
        edge_key (str): unique edge key
    """
    edge_key = str(src_user_id) + "->" + str(dest_user_id)
    return edge_key

def add_or_update_edge_in_graph(graph,
                                src_user_id,
                                dest_user_id, user_ids):
    """Add an edge to a graph (with initial weight of 1) if it does not exist.
        Add 1 to its weight if it does exist.

    Args:
        G (nx.MultiDiGraph): the generated graph with normalized edge weights
        src_user_id (int): Twitter user id for the source node in an edge being considered
            (e.g. A in A->B)
        dest_user_id (int): Twitter user id for the destination node in an edge being considered
            (e.g. B in A->B)
        ser_ids (list of int): list of all Twitter user ids in the network
            (and could be nodes in the graph)
    """
    # because can retweet a tweet that mentions yourself and we only want in_network user_ids
    if src_user_id != dest_user_id and\
        src_user_id in user_ids and dest_user_id in user_ids:
        key = generate_edge_key(src_user_id, dest_user_id)
        if graph.get_edge_data(src_user_id, dest_user_id, key) is None:
            graph.add_edge(src_user_id, dest_user_id, key=key, weight=1)
        else:
            graph[src_user_id][dest_user_id][key]["weight"] += 1

def process_potential_edges(curr_user_id,
                            user_ids,
                            tweet_ser,
                            graph):
    """Process the Twitter network influence that could potential be added as edges
        (or increment the weight of an existing edge)

    Args:
        curr_user_id (int): Twitter user id for the current user's tweets that are being processed
        user_ids (list of int): list of all Twitter user ids in the network
            (and could be nodes in the graph)
        tweet_ser (pd.Series): a Series with the relevant tweet fields needed for graph making
        G (nx.MultiDiGraph): the generated graph with normalized edge weights
    """
    replied_retweeted_quoted_user_ids = []
    # account for reply edges
    try:
        replied_to_author_ids = ast.literal_eval(tweet_ser["replied_to_author_ids"])
        for user_id_str in replied_to_author_ids:
            # if user A replied to user B, that counts as +1 for the B->A connection
            add_or_update_edge_in_graph(graph, int(user_id_str), curr_user_id, user_ids)
        replied_retweeted_quoted_user_ids.extend(replied_to_author_ids)
    except ValueError:
        pass # empty author_ids list

    # account for retweet, quote edges
    try:
        retweeted_author_ids = ast.literal_eval(tweet_ser["retweeted_author_ids"])
        quoted_author_ids = ast.literal_eval(tweet_ser["quoted_author_ids"])
        for user_id_str in retweeted_author_ids + quoted_author_ids:
            # if A retweeted or quote tweeted user B, that counts as +1 for the B->A connection
            add_or_update_edge_in_graph(graph, int(user_id_str), curr_user_id, user_ids)
        replied_retweeted_quoted_user_ids.extend(retweeted_author_ids + quoted_author_ids)
    except ValueError:
        pass # empty author_ids list

    # account for mention edges
    mention_ids = ast.literal_eval(tweet_ser["mentioned_user_ids"])
    for user_id_str in mention_ids:
        # if user A mentioned user B, that counts as +1 for the B->A connection.
        # though don't add 1 for a mention if the mention_id is the same as a
        # replied_to, retweeted, or quoted id
        if user_id_str not in replied_retweeted_quoted_user_ids:
            add_or_update_edge_in_graph(graph, int(user_id_str), curr_user_id, user_ids)

def normalize_graph_edge_weights(graph,
                                 num_tweets_per_user_dict,
                                 min_number_tweets):
    """Normalize the edge weights by dividing by total number of source
        (influencer) tweet count.

    Args:
        G (nx.MultiDiGraph): the generated graph with normalized edge weights
        num_tweets_per_user_dict (dict of int:int): each user id mapped to the total
            number of tweets they have tweeted
        min_number_tweets (int): miniumum number of tweets to have tweeted to be
            included in graph
    """
    edges_to_remove = []
    node_to_remove = []
    for _, _, key, data in graph.edges(keys=True, data=True): #_, _ -> u, v
        # using keys to be sure of direction
        src_node, dest_node = [int(node) for node in key.split("->")]
        # normalize the points by the number of total tweets from the source node
        if src_node in num_tweets_per_user_dict.keys() and\
            num_tweets_per_user_dict[src_node] >= min_number_tweets:
            graph[src_node][dest_node][key]["weight"] =\
                data["weight"] / num_tweets_per_user_dict[src_node]
            # set the label for write_dot() to use when visualizing with graphviz
            graph[src_node][dest_node][key]["label"] =\
                graph[src_node][dest_node][key]["weight"]
        else:
            # number of tweets per user is < min_number_tweets meaning this person never tweeted
            # or didn't tweet enough and therefore should not be included in the graph
            edges_to_remove.append((src_node, dest_node, key))
            if src_node not in node_to_remove:
                node_to_remove.append(src_node)

    for src_node, dest_node, key in edges_to_remove:
        graph.remove_edge(src_node, dest_node, key=key)
    for src_node in node_to_remove:
        graph.remove_node(src_node)

def make_graph(tweet_directory_name,
               min_number_tweets=100):
    """Makes a weighted, bidirectional graph to model Twitter network influence.

    Args:
        tweet_directory_name (str): name of the directory to write tweets CSV files to
        min_number_tweets (int): miniumum number of tweets to have tweeted to be included in graph

    Returns:
        G (nx.MultiDiGraph): the generated graph with normalized edge weights

    Notes:
        https://networkx.org/documentation/stable/reference/classes/multidigraph.html
    """
    # build graph nodes, but only add them if an incoming or outgoing edge exists (later)
    graph = nx.MultiDiGraph()
    fnames = [fname for fname in list(os.listdir(tweet_directory_name))\
              if os.path.splitext(fname)[1] == ".csv"]
    fnames.sort(key=lambda x: int(x.split("_")[0]))
    user_ids = [int(fname.split("_")[0]) for fname in fnames]

    # add graph edges
    num_tweets_per_user_dict = {}
    for tweets_fname in fnames:
        curr_user_id = int(tweets_fname.split("_")[0])
        tweet_df = pd.read_csv(os.path.join(tweet_directory_name, tweets_fname), index_col=0)
        # number of rows in dataframe is number of tweets in timeframe
        num_tweets_per_user_dict[curr_user_id] = tweet_df.shape[0]
        print("Processing:", tweets_fname, tweet_df.shape)

        for tweet_id in tweet_df.index:
            tweet_ser = tweet_df.loc[tweet_id]
            process_potential_edges(curr_user_id, user_ids, tweet_ser, graph)

    normalize_graph_edge_weights(graph, num_tweets_per_user_dict, min_number_tweets)
    return graph

def main(tweet_directory_name,
         output_filename):
    """Starts the graph maker using values from cmd line args or defaults.
        Writes the resulting graph to a file.

    Args:
        tweet_directory_name (str): name of the directory to write tweets
            CSV files to
        output_filename (str): name of the output file to write the graph
            as a weighted.edgelist file

    Notes:
        https://networkx.org/documentation/stable/reference/readwrite/index.html
    """
    # build network graph from tweets
    graph = make_graph(tweet_directory_name)

    # write to file
    print("Made graph with number of nodes:", len(graph.nodes),
          "and number of edges:",
          len(graph.edges(data="weight")))
    nx.write_weighted_edgelist(graph, output_filename)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch tweets from Twitter API")
    parser.add_argument("-i",
                        type=str,
                        dest="tweet_directory_name",
                        default=REHYDRATED_TWEET_DIRNAME,
                        help="The name of the directory with the tweet CSV files to\
                            process when creating the graph")
    parser.add_argument("-g",
                        type=str,
                        dest="output_filename",
                        default=GRAPH_EDGELIST_FILENAME,
                        help="The name of the output file to write the graph as a\
                            weighted.edgelist file")

    args = parser.parse_args()
    main(args.tweet_directory_name, args.output_filename)

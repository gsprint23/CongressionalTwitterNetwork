# Congressional Twitter Network

## About the Repository
This repository stores the accompanying code and data for the weighted, bidirectional graph (henceforth referred to as a "Twitter Influence Network" graph) presented in the research papers 1. Fink et. al "A centrality measure for quantifying spread on weighted, directed networks" Physica A, 2023 (DOI link: https://doi.org/10.1016/j.physa.2023.129083) and 2. Fink et. al "A Congressional Twitter network dataset quantifying pairwise probability of influence" Data in Brief (under review). This graph represents the how information flows in a network of US Congress members. Tweets from these members span the date range between February 9, 2022, and June 9, 2022. Information flow was modeled as "influence": every time Congressional members retweeted, quote-tweeted, replied to, or mentioned one another. 

Data files corresponding to data used in the research papers (adhering to Twitter's [Developer Agreement and Policy](https://developer.twitter.com/en/developer-terms/agreement-and-policy)):
* `congress_ids.txt`: the Twitter user IDs
* `congress_tweet_ids`: the Twitter tweet IDs
* `congress_network_data.json`: a JSON file containing the following Twitter Influence Network data:
  * `inList`: list of lists such that `inList[i]` is a list of all the nodes sending connections TO node `i`
  * `inWeight`: list of lists containing the connection weights (transmission probabilities) corresponding to the connections in `inList`
  * `outList`: list of lists such that `outList[i]` is a list of all the nodes receiving connections FROM node `i`
  * `outWeight`: list of lists containing the connection weights (transmission probabilities) corresponding to the connections in `outList`
  * `usernameList[i]` gives the Twitter username corresponding to node `i`
* `congress.edgelist` contains the weighted, directed edgelist for the Twitter Influence Network, in [NetworkX edgelist](https://networkx.org/documentation/stable/reference/readwrite/edgelist.html) format

Code files for using the Twitter API to fetch the data, making a "Twitter Influence Network" graph, and running the Viral Centrality measure algorithm over the graph:
* `tweet_rehydrater.py`: code for rehydrating tweet IDs
  * Makes use of utility variables and functions in `utils.py`
  * See Twitter's [https://developer.twitter.com/en/developer-terms/more-on-restricted-use-cases](https://developer.twitter.com/en/developer-terms/more-on-restricted-use-cases) for more information about rehydration
* `tweet_fetcher.py`: code for fetching tweets from a user ID
  * Makes use of utility variables and functions in `utils.py`
* `graph_maker.py`: code for making a "Social Network" graph from rehydrated or fetched tweets
* `test_graph_maker.py`: unit test for graph_maker. This file helps explain how influence is modeled in a "Twitter Influence Network" graph
* `compute_vc.py`: code to implement the Viral Centrality portion of Fig. 2A from "A centrality measure for quantifying spread on weighted, directed networks" (uses the function in `viral_centrality.py`)
* `histogram_weights.py`: code to replicate Fig. 2B from "A centrality measure for quantifying spread on weighted, directed networks"

The code is written in Python and uses the following non-standard packages:
* [`tweepy`](https://www.tweepy.org/) for fetching tweets from the [Twitter API](https://developer.twitter.com/en)
* [`numpy`](https://numpy.org/), [`scipy`](https://scipy.org/), and [`pandas`](https://pandas.pydata.org/) for processing/storing tweet data
* [`networkx`](https://networkx.org/) for graph representation
* [`matplotlib`](https://matplotlib.org/) for figure generation

## Setup
1. Apply for and get approved for [Twitter API Academic Research access level](https://developer.twitter.com/en/products/twitter-api/academic-research)
1. Create a [Twitter API bearer token](https://developer.twitter.com/en/docs/authentication/overview)
  * Note: you will need access to the [full archive search endpoint](https://developer.twitter.com/en/docs/twitter-api/tweets/search/quick-start/full-archive-search) to run the `tweet_fetcher.py` script
2. Clone the repo
  ```sh
  git clone https://github.com/gsprint23/CongressionalTwitterNetwork
  ```
3. Install Python packages
  ```sh
  pip install -r requirements.txt
  ```
4. Paste your bearer token in a `twitter_keys.json` file (`utils.py` opens this file to load your token)
```json
{
  "bearer_token": "YOUR TOKEN HERE"
}
```

## Usage
### Research Paper's Original Congressional Tweets
The [Twitter Developer Agreement and Policy](https://developer.twitter.com/en/developer-terms/agreement-and-policy) states:  
>If you provide Twitter Content to third parties, including downloadable datasets or via an API, you may only distribute Tweet IDs, Direct Message IDs, and/or User IDs (except as described below). We also grant special permissions to academic researchers sharing Tweet IDs and User IDs for non-commercial research purposes.

Consequently, only the originally used 530 User IDs and 179,974 Tweet IDs are included in this repository. The `congress_ids.txt` file contains the Twitter User IDs and the `congress_tweet_ids` folder contains the originally fetched tweets (organized into files by User ID). To create a "Twitter Influence Network" graph from this data, the tweets need to be "rehydrated."

### Tweet Rehydrating
According to [Twitter's "Redistribution of Twitter content"](https://developer.twitter.com/en/developer-terms/more-on-restricted-use-cases):  
> If you need to share Twitter content you obtained via the Twitter APIs with another party, the best way to do so is by sharing Tweet IDs, Direct Message IDs, and/or User IDs, which the end user of the content can then rehydrate (i.e. request the full Tweet, user, or Direct Message content) using the Twitter APIs. This helps ensure that end users of Twitter content always get the most current information directly from us.

Therefore, run the `tweet_rehydrater.py` script to rehydrate the tweets provided in `congress_tweet_ids`. The rehydration process can use one of these endpoints:
1. [`/2/tweets/:id`](https://developer.twitter.com/en/docs/twitter-api/tweets/lookup/api-reference/get-tweets-id) (single tweet ID)
1. [`/2/tweets`](https://developer.twitter.com/en/docs/twitter-api/tweets/lookup/api-reference/get-tweets) (list of Tweet IDs)

The `tweet_rehydrater.py` script uses the `/2/tweets` endpoint to rehydrate the tweets provided in `congress_tweet_ids` in chunks of 100 (current API max number per request). It will only request, parse, and store the minimum information needed for the `graph_maker.py` script to generate a "Twitter Influence Network" graph. Note that not all the rehydrated Tweets are going to match the original Tweets used to created the graph used in the paper. For more information, please see the section on [Twitter API Tweet Response Variability](#twitter-api-tweet-response-variability) below.

Example runs:
```sh
python tweet_rehydrater.py
```
Rehydrates tweets using ids in files in default directory (`congress_tweet_ids`). Writes the rehydrated tweets to the default directory (`rehydrated_tweet_data`)

```sh
python tweet_rehydrater.py -i input_dirname -r rehydrated_dirname
```
Rehydrates tweets using ids in files in `input_dirname`. Writes the rehydrated tweets to `rehydrated_dirname`

### Graph Making
To understand how the graph is constructed and how influence is represented in the graph, please read and understand the `test_graph_maker.py` file first. It includes a pytest unit test for creating a simple four node graph. To install pytest: `pip install pytest` then run: `pytest test_graph_maker.py`

Example runs:
```sh
python graph_maker.py
```
Builds a graph using tweets in files in default directory (`rehydrated_tweet_data`). Writes the graph as a weighted edgelist to the default filename (`network.weighted.edgelist`)

```sh
python graph_maker.py -i input_dirname -g graph_filename
```
Builds a graph using tweets in files in `input_dirname`. Writes the graph as a weighted edgelist to `graph_filename`

Note: The original Congressional graph cannot be reproduced from the original `congress_tweet_ids` files. For more information, please see the section on [Twitter API Tweet Response Variability](#twitter-api-tweet-response-variability) below.

### Computing Viral Centrality
Runs the Viral Centrality measure algorithm over the `congress_network_data.json` graph data.

Example run:
```sh
python compute_vc.py
```

## Notes on the Twitter API
### Tweet Fetching
If you would like to fetch Tweets for a different list of user IDs and/or different date range, Tweets can be fetched from a particular user using the Twitter API. Here are endpoints that can be used for this:
1. [`/2/users/:id/tweets`](https://developer.twitter.com/en/docs/twitter-api/tweets/timelines/api-reference/get-users-id-tweets) (timeline search)
1. [`/2/tweets/search/all`](https://developer.twitter.com/en/docs/twitter-api/tweets/search/api-reference/get-tweets-search-all) (full archive search)
1. [`/2/tweets/search/recent`](https://developer.twitter.com/en/docs/twitter-api/tweets/search/api-reference/get-tweets-search-recent) (recent 7 day search)

For the aforementioned research paper, the `/2/users/:id/tweets` endpoint (timeline search) was used to fetch up to 3,200 recent tweets for a user. For reproducibility, the `tweet_fetcher.py` script includes the code necessary to fetch these tweets using the aforementioned paper date range and the `/2/tweets/search/all` endpoint (full archive search); however, using the full archive search endpoint may return different tweets/tweet content for the same query (and when compared to tweets originally requested via timeline search). For more information, please see the section on [Twitter API Tweet Response Variability](#twitter-api-tweet-response-variability) below.

Example runs:
```sh
python tweet_fetcher.py
```
Fetches all tweets from user ids in default file (`congress_ids.txt`) between default start and end UTC timestamps (`2022-02-09 22:01:13+00:00` and `2022-06-09 00:00:00+00:00`). Writes the fetched tweets to the default directory (`fetched_tweet_data`). 

```sh
python tweet_fetcher.py -i input_filename -f fetched_dirname -s start_timestamp -e end_timestamp -l limit
```
Fetches `limit`  number of tweets from user ids in file (`input_filename`) between start and end UTC timestamps (`start_timestamp` and `end_timestamp`). Writes the fetched tweets to `fetched_dirname`. Note that `limit` must be between 10 and 500.

### Twitter API Tweet Response Variability
Tweets returned by the Twitter API may be different over time due to several reasons:
1. A tweet may be edited (within a certain time period)
1. A tweet may be deleted
1. An account may change from public/private and vice versa (affecting tweet availability)
1. An account could be suspended or deleted
1. Inexplicable anomalies with the API. Here are a few I ran across on the Twitter forums:
    1. https://twittercommunity.com/t/assurance-over-missing-tweets/185362
    1. https://twittercommunity.com/t/missing-tweets-in-search-results-when-comparing-to-twitter-website/151088/10
    1. https://twittercommunity.com/t/tweets-not-showing-up-in-search/181567/2

## License
Distributed under the MIT License. See `LICENSE.txt` for more information.

## Contact
Code/data: Gina Sprint - [@gsprint23](https://github.com/gsprint23) - sprint@gonzaga.edu  
Paper/research: Chris Fink - finkt@gonzaga.edu
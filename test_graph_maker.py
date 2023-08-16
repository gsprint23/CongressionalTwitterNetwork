"""test_graph_maker.py
Tests the make_graph() function in graph_maker.py

@author Gina Sprint
@date 6/15/23
"""

import os
import networkx as nx

from graph_maker import make_graph

GRAPH_VIZ = False # if True need to install https://graphviz.org/
TEST_DIRNAME = "test_data"

# 0 makes 5 tweets
# 0 quoted 2 => +1 to 2->0
# 0 retweeted 2 => +1 2->0
# 0 retweeted 2 => +1 2->0
# 0 mentioned 1, 2, 3  => +1 1->0, => +1 2->0, => +1 3->0

# 1 makes 4 tweets
# 1 mentioned 0 => +1 0->1

# 2 makes 3 tweets
# 2 retweeted 0 => +1 0->2
# 2 quoted 3 => +1 3->2
# 2 replied to 3 => +1 3->2

# 3 makes 2 tweets

# 2->0 weight 4 (normalized 4 / 3 total tweets by 3 = 1.33)
# 1->0 weight 1 (normalized 1 / 4 total tweets by 1 = 0.25)
# 3->0 weight 1 (normalized 1 / 2 total tweets by 3 = 0.5)
# 0->1 weight 1 (normalized 1 / 5 total tweets by 0 = 0.2)
# 0->2 weight 1 (normalized 1 / 5 total tweets by 0 = 0.2)
# 3->2 weight 2 (normalized 2 / 2 total tweets by 3 = 1.0)

def draw_dot_graph(graph,
                   graph_fname):
    """Visualizes the test graph with graphviz.

    Args:
        graph (nx.MultiDiGraph): the graph to visualize
        graph_fname (str): name of the file to write the visualization to
    """
    # takes too long to run with 100+ nodes
    # but good for visualizing test data
    dot_fname = graph_fname.split(".")[0] + ".dot"
    pdf_fname = graph_fname.split(".")[0] + ".pdf"
    nx.drawing.nx_pydot.write_dot(graph, dot_fname)
    os.popen("dot -Tpdf " + dot_fname + " -o " + pdf_fname)

def test_build_graph():
    """Tests the build_graph function with test data in test_data directory.

    Notes:
        Uses pytest: https://docs.pytest.org/en/7.3.x/
    """
    graph = make_graph(TEST_DIRNAME, min_number_tweets=1)
    assert graph[0][1]["0->1"]["weight"] == 0.2
    assert graph[0][2]["0->2"]["weight"] == 0.2
    assert graph[1][0]["1->0"]["weight"] == 0.25
    assert graph[2][0]["2->0"]["weight"] == 1 + 1 / 3
    assert graph[3][0]["3->0"]["weight"] == 0.5
    assert graph[3][2]["3->2"]["weight"] == 1.0

    # write graph viz to file
    if GRAPH_VIZ:
        graph_fname = os.path.join(TEST_DIRNAME, "graph.png")
        draw_dot_graph(graph, graph_fname)

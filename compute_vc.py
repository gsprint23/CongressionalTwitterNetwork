# -*- coding: utf-8 -*-
"""compute_vc.py
Code to implement the Viral Centrality measure to replicate
the Viral Centrality portion of Fig. 2A from"A centrality
measure for quantifying spread on weighted, directed networks"
Uses the function in viral_centrality.py

@author Christian G. Fink
@date 7/15/23
"""
from viral_centrality import viral_centrality
import json
import numpy as np
from matplotlib import pyplot as plt

tol = 0.001

f = open('congress_network_data.json')
data = json.load(f)

inList = data[0]['inList']
inWeight = data[0]['inWeight']
outList = data[0]['outList']
outWeight = data[0]['outWeight']
usernameList = data[0]['usernameList']

num_activated = viral_centrality(inList, inWeight, outList, Niter = -1, tol = tol)

plt.scatter(np.array(range(len(num_activated))),num_activated,color='red',label='Viral Centrality')
plt.xlabel('Node ID',fontsize=15)
plt.ylabel('Avg Number Activaated',fontsize=15)


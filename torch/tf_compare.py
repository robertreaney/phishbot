import math
import torch
import torch.nn as nn
import torch.nn.functional as F
import time
import os
import pandas as pd
import torchtext
import numpy as np
from torch.utils.data import TensorDataset

######################
embedding_dim = 50
rnn_units = 100
seq_length = 100

# compare outputs to tf

#data import
data = pd.read_csv("C:/Users/rober/Documents/projects/phish_setlistbot/datacollection/final.csv")

test = []
test.append(data[data.date == "2019-07-12"].Song)
test.append(data[data.date == "2019-07-13"].Song)
test.append(data[data.date == "2019-07-14"].Song)
test.append(data[data.date == "2019-08-30"].Song)
test.append(data[data.date == "2019-08-31"].Song)
test.append(data[data.date == "2019-09-01"].Song)

data3point0 = data[(data.date > "2009-01-01") & (data.date < "2019-07-12")]

df = data3point0['Song'].copy()
del data, data3point0

#vocab
from vocabulary import Vocab
translate = Vocab(df)
translate.ids_from_songs(["eaefe"])
translate.ids_from_songs(['Possum', 'Sigma Oasis'])
translate.ids_from_songs("Fluffhead")
translate.songs_from_ids([0,1,2])
translate.songs_from_ids([111111])
len(translate.vocab_dict) #this returns 510, but length of true vocab doesn't include ' ' or 'unknown
# df transformation
all_ids = translate.ids_from_songs(list(df))  #this does not accept pandas series, needs to be a list
len(all_ids)

from processing import input_label_split
#all_ids

x, y = input_label_split(all_ids, sequence_length=100, overlap_inputs=True)

ds = torch.utils.data.TensorDataset(x,y)
dataset = torch.utils.data.DataLoader(ds, batch_size=, shuffle=True)

xb, yb = next(iter(dataset))  #(batchsize x sequence_length), batchsize


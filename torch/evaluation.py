import numpy as np
import torch
import pandas as pd
from collections import Counter


#fit model
def fit(model, opt, loss_func, train_dl, valid_dl=None, epochs=2):
    #dev = torch.device("cuda:0") if torch.cuda.is_available() else torch.device("cpu")
    dev = torch.device("cpu")
    #writer = SummaryWriter()
    for epoch in range(epochs):
        #training set
        model.train()
        tr_loss=[]
        for xb, yb in train_dl:
            pred = model(xb)
            for ii in range(len(yb)):
                loss = loss_func(pred[ii], yb[ii])
                if ii < len(yb):
                    loss.backward(retain_graph=True)
                if ii == len(yb):    
                    loss.backward(retain_graph=False)
            tr_loss.append(loss)

            opt.step()
                #opt.zero_grad()
            opt.zero_grad()
        print(epoch, sum(tr_loss)/len(tr_loss))
        #writer.add_scalar('runs',sum(tr_loss)/len(tr_loss), epoch)
        #validation step   #this doesnt work anymore
        if valid_dl != None:
            valid_loss = []
            model.eval()
            with torch.no_grad():
                for xb, yb in valid_dl:
                    pred = model.forward(xb)
                    for ii in range(len(yb)):
                        loss = loss_func(pred[ii], yb[ii])
                        valid_loss.append(loss)
                    #valid_loss = sum(loss_func(model(xb.cuda()).view(len(xb),-1), yb.cuda()) for xb, yb in valid_dl)
                    #valid_loss = statistics.mean(loss_func(self.forward(xb), yb) for xb, yb in valid_dl)
            print("validation", epoch, sum(valid_loss)/len(valid_loss))


####### make class to handle the predict/eval/update loop for implementing model
class NextNetEvaluator():
    def __init__(self, model, translate): ##lets make eval_feed an np.array(df[-sequence_length:])
        """
        NextNet evaluation class. This object handles predictions by holding an array of the most recent songs.
            Args:   model = a fitted NextNet object
                    translate = Vocab() instantiation that holds the song key dictionary for the current training 
        """
        self.model = model
        self.translate = translate #songs needed to do preds, length = sequence_length
    def predict(self, eval_feed, show_length = 25, vote_ensemble=10, voting='Max'): #requires passing of the a 
        """
        Makes predictions based on most recent sequence_length number of songs
            Args:   eval_feed = most recent sequence_length number of songs to base predictions off of
                    show_length = length of next show
                    vote_ensemble = repeats prediction process this number of times. uses voting scheme to finalize final return. default 10 has shown 30% performance increase
                    voting = voting scheme fot vote_ensemble > 1. Probability voting NOT RECCOMENDED. performs worse than vote_ensemble=1.
        """
        dev = torch.device("cuda:0") if torch.cuda.is_available() else torch.device("cpu")
        #dev = torch.device("cpu")
        assert voting in ['Max', 'max', 'Probs', 'prob', 'probs', 'Prob', 'p', 'm'], "Enter valid voting scheme max/prob currently supported"
        self.most_recent_songs = eval_feed
        vocab_length = len(self.translate.vocab_dict)    
        # try:
        ids = self.translate.ids_from_songs(eval_feed).to(dev).reshape(1,-1)
        # except:
        #     "The Vocab() instance 'translate' is not fitted. Instantiate the object with a dataset so this class can reference its vocab_dict attribute."
        ensemble_history = []
        for ii in range(vote_ensemble):
            newshow = []
            states = None
            sm = torch.nn.Softmax(0)
            #for ii in range(show_length): #25 is a placeholder for our future generation of how many songs in the next show
            while len(newshow) < show_length:
                #tens = torch.tensor([ids])
                self.model.eval()
                with torch.no_grad():
                    logits, states_candidate = self.model(ids,states, return_states=True)
                    #the prob we care about is prob[0][99]
                    probs = sm(logits[0][-1]).cpu().numpy()
                    probs = probs/probs.sum()
                    random_prob = np.random.choice(np.arange(vocab_length),p=probs)
                    next_song = self.translate.songs_from_ids(random_prob)
                    if next_song not in newshow: #dont return duplicates
                        newshow.append(next_song)
                        states = states_candidate
                        ids[0] = torch.cat((ids[0][1:], self.translate.ids_from_songs([next_song]).to(dev)))
            ensemble_history.append(newshow)
        if vote_ensemble == 1:
            return newshow
        else:
            newshow = [] #can reuse this object name. will save memory and sounds intuitive
            ensemble_history = [item for sublist in ensemble_history for item in sublist]
            #now do i want to take best 25 unique entries or sample 25 times until i get 25 unique entries?
            if voting in ['Max', 'm', 'max']:
                #songs = list(set(ensemble_history))
                #counts = [ensemble_history.count(ii) for ii in songs]
                counts = Counter(ensemble_history)
                #if max_choice == 'random': #Counter() uses alphabetical order to handle ties in count
                return [song for song, count in counts.most_common(show_length)]
                #else: #use random choice to solve ties
            elif voting in ['Prob', 'p', 'prob', 'Probs', 'Prob']:
                while len(newshow) < show_length:
                    candidate = np.random.choice(list(ensemble_history)) #get one song from list of candidates
                    if candidate not in newshow:
                        newshow.append(candidate)
            return newshow
#compare predict setlist to the actual show
    def eval_preds(self, preds, targets, score=False):
        """
        This function evaluates predictions against a true setlist.
        """
        if score: #eventually the true reddit scoring system will go here
            pass
        else:
            targets = np.asarray(targets) #usually our test set is a pandas df originally. need it to be a np array
            winners = []
            count = 0
            for song in preds:
                if song in targets:
                    count += 1
                    winners.append(song)
            return winners, count
#move data around to do the predict/eval loop for the next show
    def update_with_show(self, observed_show):
        """
        Updates eval_feed/most_recent_songs stored in this class with an observed show
        """
        new_n = len(observed_show)
        try:
            self.most_recent_songs = np.append(self.most_recent_songseval_feed[new_n:], observed_show)
        except:
            pass
        try:
            self.most_recent_songs = pd.concat([self.most_recent_songs[len(observed_show):], observed_show])
        except:
            "Check type of observed_show against self.eval_feed"

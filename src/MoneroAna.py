import requests
import json
import numpy as np
import matplotlib.pyplot as plt
import ot
import gtda
import pymc as pm
import random

class block:
    def __init__(self, block):
        r = requests.get("http://127.0.0.1:8081/api/block/{}".format(block))
        data = json.loads(r.text)['data']
        
        for k,v in data.items():
            setattr(self, k, v)
            #print(type(i), type(j))
            #try:
            #    exec("self.{}={}".format(i,j))
            #except SyntaxError:
            #    exec("self.{}='{}'".format(i,j))
            
        self.sources = []
        self.sinks = []
                        
    def get_txs(self):
        return [tx(i['tx_hash']) for i in self.txs]
                                
    def __str__(self):
        return str(self.tx_hash)
           
class tx:
    def __init__(self, tx_hash):
        r = requests.get("http://127.0.0.1:8081/api/transaction/{}".format(tx_hash))
        data = json.loads(r.text)['data']
        for k,v in data.items():
            setattr(self, k, v)
        #self.tx_hash = tx_hash
        #self.coinbase = self.data['coinbase']
        if self.coinbase == False:
            self.get_rings()
        #elf.inputs = self.data['inputs']
            #mixins = [[j for j in i['mixins']] for i in self.dat['data']['inputs']]
            
        self.sources = []
        self.sinks = []
            
    def get_rings(self):
        self.rings = [ring(i, self.block_height) for i in self.inputs]

    def __str__(self):
        return str(self.tx_hash)
        
class ring:
    def __init__(self, inputs, refheight):
        self.mixins = [i['tx_hash'] for i in inputs['mixins']]
        self.block_no = [i['block_no'] for i in inputs['mixins']]
        self.youngest = self.block_no[-1]
        self.oldest = self.block_no[0]
        self.refheight = refheight
        #self.sources = []
        self.sinks = []
        #self.tx_hash = tx_hash
        #self.coinbase = self.dat['data']['coinbase']
        
    def get_mixins(self):
        return [tx(i) for i in self.mixins]
    
    def get_distribution(self):
        n = len(self.mixins)
        self.probabilities = pymc.Categorical([1/n for i in range(n)])
        
    def get_txs(self):
        return [tx(i) for i in self.mixins]
    

def get_oldest_path(txo):
    
    mxn = txo.mixin
    while txo.coinbase==False:
        idx = np.argmin([i.oldest for i in txo.rings])
        txo = tx(txo.rings[idx].mixins[0])
        mxn = txo.mixin*mxn
        print(mxn)
        yield txo
        
def get_youngest_path(txo):
    mxn = txo.mixin
    while txo.coinbase==False:
        idx = np.argmax([i.youngest for i in txo.rings])
        txo = tx(txo.rings[idx].mixins[-1])
        yield txo

def get_random_paths(txo):
    
    while txo.coinbase==False:
        txo = tx(random.choice(random.choice(txo.rings).mixins))
        yield txo
        
def taint(txo, display=100, depth=1000000, maxtx = 5000000, refheight = None):
    if refheight == None:
        refheight = txo.block_height
    current = 0
    coinbases = []
    if txo.coinbase == True:
        coinbases.append(txo.block_height)
        l = []
    else:
        l = [txo]
        
    yield l, coinbases
    
    cnt = 0
    #n = len(coinbases)
    loop = 0
    l2 = []
    while len(l)>0 and cnt<maxtx:
        loop+=1
        print("loop", loop)
        l1 = []
        newcoinbase = 0
        for k in l:
            for j in k.rings:
                for h,i in zip(j.block_no,j.mixins):
                    if np.abs(refheight-h)<depth:
                        txnew = tx(i)
                        if txnew.coinbase==True:
                            coinbases.append(txnew.block_height)
                            newcoinbase+=1
                        else:
                            l1.append(txnew)
                            cnt+=1
                            if cnt%display==0:
                                print(cnt)
                    else:
                        l2.append(i)
        yield l1, coinbases[-newcoinbase:]
        
        l = l1
    yield l2
        
        
def taint_ring(ring, depth=1000000, maxtx=5000000,refheight=None):
    if refheight==None:
        refheight = ring.block_height
    
    ttrees_ring = [taint(i, refheight=refheight, depth=depth) for i in ring.get_txs()]
    print(len(ttrees_ring))
    
    while 1>0:
        yield [[j for j in i] for i in ttrees_ring]
        
def cotxs(ttree1, ttree2):
    l21 = ttree1[-1]
    l22 = ttree2[-1]
    
    txs = []
    cbs = []
    for i,j in ttree1[:-1]:
        txs+=i
        cbs+=j
    
    txs2 = []
    cbs2 = []
    for i,j in ttree2[:-1]:
        txs2+=i
        cbs2+=j
    
    txs_hashes = [i.tx_hash for i in txs]
    txs2_hashes = [i.tx_hash for i in txs2]
    print(len(txs_hashes), len(txs2_hashes))
    
    return [i for i in set(txs_hashes) if i in txs2_hashes], [i for i in set(cbs) if i in cbs2] #, [i for i in l21 if i in l22]

def list_intersection(list1, list2):
    
    list1, list2 = sorted(list1), sorted(list2)
    n1, n2 = len(list1), len(list2)
    intersection = []
    i = 0
    j = 0
    
    while i < n1 and j < n2:
        if list1[i]==list2[j]:
            intersection.append(list1[i])
            i+=1
            j+=1
        elif list1[i] < list2[j]:
            i +=1
        else:
            j+=1
            
    return set(intersection)

    
    
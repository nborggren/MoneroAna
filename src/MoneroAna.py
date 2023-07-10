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
        self.rings = [ring(i) for i in self.inputs]

    def __str__(self):
        return str(self.tx_hash)
        
class ring:
    def __init__(self, inputs):
        self.mixins = [i['tx_hash'] for i in inputs['mixins']]
        self.block_no = [i['block_no'] for i in inputs['mixins']]
        self.youngest = self.block_no[-1]
        self.oldest = self.block_no[0]
        
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
        
def taint(txo, display=100, depth=1000000, maxtx = 5000000):
    current = 0
    coinbases = []
    if txo.coinbase == True:
        coinbases.append(txo.block_height)
        l = []
    else:
        l = [txo]
        
    yield l, coinbases
    
    cnt = 0
    loop = 0
    l2 = []
    while len(l)>0 and cnt<maxtx:
        loop+=1
        print("loop", loop)
        l1 = []
        for k in l:
            for j in k.rings:
                for h,i in zip(j.block_no,j.mixins):
                    if txo.block_height-h<depth:
                        txnew = tx(i)
                        if txnew.coinbase==True:
                            coinbases.append(txnew.block_height)
                        else:
                            l1.append(txnew)
                            cnt+=1
                            if cnt%display==0:
                                print(cnt)
                    else:
                        l2.append(i)
        yield l1, coinbases
        l = l1
    yield l2
        
        
def taint_ring(ring, depth=1000000, maxtx=5000000):
    ttrees_ring = [taint(i, depth=depth) for i in ring.get_txs()]
    
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
    
    return [i for i in set(txs_hashes) if i in txs2_hashes], [i for i in set(cbs) if i in cbs2], [i for i in l21 if i in l22]
    
    
    
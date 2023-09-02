import requests
import json
import numpy as np
import matplotlib.pyplot as plt
import ot
import gtda
from gtda import homology
import pymc as pm
import random
import pandas as pd

VR = homology.VietorisRipsPersistence(homology_dimensions=[0])

class registry:
    def __init__(self, txs):
        self.txs = {}
        for i in txs:
            self.txs[i.tx_hash] = i
            
    def add(self, txs):
        for i in txs:
            self.txs[i.tx_hash] = i
            
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
                        
    def get_txs(self, registry={}):
        return [tx(i['tx_hash'], registry=registry) for i in self.txs]
                                
    def __str__(self):
        return str(self.tx_hash)
    
    def __lt__(self, other):
        return self.block_height>other.block_height
           
class tx:
    def __init__(self, tx_hash, registry={}):
        if tx_hash in registry:
            self = registry[tx_hash]
        else:
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
            registry[tx_hash] = self
            
    def get_rings(self):
        #print(self.block_height)
        self.rings = [ring(i, self) for i in self.inputs]
        
    def taint(self, height, registry={}):
        #self.taint = {}
        return [i.get_mixins(max_height=height, registry=registry) for i in self.rings]

    def __str__(self):
        return str(self.tx_hash)
    
    def __lt__(self, other):
        return self.block_height > other.block_height
        
class ring:
    def __init__(self, inputs, txo):
        self.mixins = [i['tx_hash'] for i in inputs['mixins']]
        self.block_no = [i['block_no'] for i in inputs['mixins']]
        self.public_key = [i['public_key'] for i in inputs['mixins']]
        self.youngest = self.block_no[-1]
        self.oldest = self.block_no[0]
        self.txo = txo
        self.block_height = txo.block_height
        self.key_image = inputs['key_image']
        #self.sources = []
        self.sinks = []
        
        self.get_pers_diagram()
        #self.tx_hash = tx_hash
        #self.coinbase = self.dat['data']['coinbase']
        
    def get_mixins(self, registry={}, min_height = -1, max_height = -1):
        mixins = []
        for i,j in zip(self.block_no,self.mixins):
            #print(i,j)
            if i > max_height or i < min_height:
                continue
            else:
                #self.txo.sinks.append(j)
                if j in registry:
                    registry[j].sources.append(self.txo.tx_hash)
                    registry[self.txo.tx_hash].sinks.append(j)
                    mixins.append(registry[j])
                else:
                    registry[j] = tx(j, registry=registry)
           
                    registry[j].sources.append(self.txo.tx_hash)
                    registry[self.txo.tx_hash].sinks.append(j)
                    mixins.append(registry[j])
        
        return mixins
    
    def get_distribution(self):
        n = len(self.mixins)
        self.probabilities = pymc.Categorical([1/n for i in range(n)])
        
    def get_pers_diagram(self):
        pc = np.array(self.block_no).reshape(-1,1)
        self.pers_diagram = VR.fit_transform([pc])[0]
        #self.pers_diagram[:,1] = np.log10(self.pers_diagram[:,1])

    def __str__(self):
        return str(self.mixins)
    
    def __iter__(self):
        for i,j in zip(self.block_no[::-1], self.mixins[::-1]):
            yield i, tx(j)
                       
    def __lt__(self, other):
        return self.youngest > other.youngest
    

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

def get_random_path(txo, registry={}, max_height = -1):
    
    mxn = len(txo.inputs)
    
    path = []
    current_hash = txo.tx_hash
    
    while txo.coinbase==False and txo.block_height > max_height:
        idx, r = random.choice(list(enumerate(txo.rings)))
        idx2, next_hash = random.choice(list(enumerate(r.mixins)))
        #print(r.public_key[idx2])
        #print(txo.outputs)

        #path.append((idx, idx2))
        
        if next_hash in registry:
            txo = registry[next_hash]
        else:
            txo = tx(next_hash, registry=registry)
         
        #print(r.public_key[idx2])
        #print(txo.outputs)
        oidx = [i for i,j in enumerate(txo.outputs) if j['public_key']==r.public_key[idx2]][0]
        #print(idx, idx2, oidx)
            
            
        txo.sources.append(current_hash)       
        registry[current_hash].sinks.append(next_hash)
        
        current_hash = next_hash
        
        mxn = txo.mixin*mxn/len(txo.outputs)
        #print(mxn)
        
        path.append((idx, idx2, oidx, txo))
        yield txo
        

        
    yield path
    
def sample_paths(n, txo, registry = {}, max_height = -1):
    paths = []
    for i in range(n):
        if i%1000==0:
            print(i)
        tmp = [j for j in get_random_path(txo, registry=registry, max_height = max_height)]
        paths.append(tmp[-1])
    return paths
        
def get_random_tree(txo, registry={}, max_height = -1):
    
    paths = [txo]
    
    if txo.coinbase==False and txo.block_height > max_height:
        for idx,r in enumerate(txo.rings):
            idx2, next_hash = random.choice(list(enumerate(r.mixins)))
            #print(idx2)

        
            if next_hash in registry:
                child = registry[next_hash]
            else:
                child = tx(next_hash, registry=registry)
            
            txo.children.append(child)

    return txo.children


#exhaustive search struggles
def taint(txo, display=100, depth=1000000, maxtx = 5000000, refheight = None):
    if refheight == None:
        refheight = txo.block_height
    current = 0
    coinbases = []
    seen = {}
    seen[txo.tx_hash] = [txo]
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
                    if np.abs(refheight-h)<depth and i not in seen.keys():
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

    
    
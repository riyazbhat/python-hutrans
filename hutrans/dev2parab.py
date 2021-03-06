#!/usr/bin/env python 
#!-*- coding: utf-8 -*-

"""
Transliteration Tool:
Devnagri to Persio-Arabic transliterator for hindi-urdu transliteration
"""

import os
import re
import sys
import codecs
import warnings

import numpy as np
from scipy.sparse import csc_matrix
from sklearn.externals import joblib as jl

import viterbi
from converter_indic import wxConvert
from one_hot_repr import OneHotEncoder as ft

warnings.filterwarnings("ignore")

__author__ = "Irshad Ahmad"
__version__ = "1.0"
__email__ = "irshad.bhat@research.iiit.ac.in"

class DP_Transliterator():
    """Transliterates words from Hindi to Urdu"""

    def __init__(self):        

        self.n = 4
	self.space = '^^'
        self.lookup = dict()
	self.esc_char = chr(0)
        self.con = wxConvert(order='utf2wx')
        path = os.path.abspath(__file__).rpartition('/')[0]
        self.clf = jl.load('%s/models/hu_sparse-clf' %path)
        self.vec = jl.load('%s/models/hu_sparse-vec' %path)

        try:
            with codecs.open('%s/extras/punkt.map' %path, 'r', 'utf-8') as punkt_fp: 
                self.punkt = {line.split()[0]: line.split()[1] for line in punkt_fp}
        except IOError, e:
            print >> sys.stderr, e
            sys.exit(0)

    def feature_extraction(self, letters):
        out_word = list()
        dummies = ["_"] * self.n
        context = dummies + letters + dummies
        for i in range(self.n, len(context)-self.n):
            current_token = context[i]
            wordContext = context[i-self.n:i] + [current_token] + context[i+1:i+(self.n+1)]
            word_ngram_context = wordContext + ["%s|%s" % (p,q) for p,q in zip(wordContext[:-1], wordContext[1:])] +\
                ["%s|%s|%s" % (r,s,t) for r,s,t in zip(wordContext[:-2], wordContext[1:], wordContext[2:])] +\
                ["%s|%s|%s|%s" % (u,v,w,x) for u,v,w,x in zip(wordContext[:-3],wordContext[1:],wordContext[2:],wordContext[3:])] 
            out_word.append(word_ngram_context)

        return out_word

    def predict(self, word):
        X = self.vec.transform(word)
        scores = X.dot(self.clf.coef_.T).toarray()
        n_classes = len(self.clf.classes_)

        y = viterbi.decode(scores, self.clf.intercept_trans_, self.clf.intercept_init_, self.clf.intercept_final_)

        y =  [self.clf.classes_[pred] for pred in y]

        return re.sub('_','',''.join(y))

    def case_trans(self, word):
        if not word:
            return u''
        if word in self.lookup:
            return self.lookup[word]
        if not word.isalpha():
            non_alpha = list(word)
            for i,char in enumerate(word):
                non_alpha[i] = char
                if char in self.punkt:
                    non_alpha[i] = self.punkt[char]
            non_alpha = ''.join(non_alpha)
            self.lookup[word] = non_alpha
            return non_alpha
        word_feats = ' '.join(word).replace(' a', 'a').replace(' Z', 'Z')
        word_feats = word_feats.encode('utf-8').split()
        word_feats = self.feature_extraction(word_feats)
        op_word = self.predict(word_feats).decode('utf-8')
        self.lookup[word] = op_word

        return op_word

    def transliterate(self, text):
        tline = str()
	text = re.sub(r'([a-zA-Z]+)', r'%s\1' %(self.esc_char), text)
	lines = text.split("\n")
	for line in lines:
	    if not line.strip():
                tline += "\n"
            line = self.con.convert(line).decode('utf-8')  # Convert to wx
            line = line.replace(' ', self.space)
            line = ' '.join(re.split(r"([^a-zA-Z%s]+)" %(self.esc_char), line)).split()
            for word in line:
		if word == self.space:
		    tline += " "
		elif word[:2] == self.esc_char:
		    tline += word[2:].encode('utf-8')
		else:
		    op_word = self.case_trans(word)
		    tline += op_word.encode('utf-8')
	    tline += "\n"
       
	tline = tline.replace(self.space, " ").strip()
        return tline

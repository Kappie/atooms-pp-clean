# This file is part of atooms
# Copyright 2010-2014, Daniele Coslovich

from .correlation import filter_species

"""Fake decorator to compute partial correlation functions.
Uses filters internally"""

class Partial(object):

    def __init__(self, corr_cls, species, *args, **kwargs):
        self._corr_cls = corr_cls
        self._species = species
        self._args = args
        self._kwargs = kwargs
                
    def compute(self):
        self.partial = {}
        for i in range(len(self._species)):
            for j in range(len(self._species)):
                if j<i:
                    continue
                # Instantiate a correlation object 
                # with args passed upon construction
                isp = self._species[i]
                jsp = self._species[j]
                self.partial[(isp,jsp)] = self._corr_cls(*self._args, **self._kwargs)
                self.partial[(isp,jsp)].add_filter(filter_species, isp)
                # Slight optimization: avoid filtering twice when isp==jsp
                if isp != jsp:
                    self.partial[(isp,jsp)].add_filter(filter_species, jsp)
                self.partial[(isp,jsp)].compute()
                self.partial[(isp,jsp)].tag = '%d-%d' % (isp, jsp)

    def do(self):
        self.compute()
        for k in self.partial:
            self.partial[k].write()

        

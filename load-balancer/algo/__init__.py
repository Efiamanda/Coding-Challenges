import abc
from typing import List
from backend.backend import backend

class Algo(metaclass=abc.ABCMeta):
    @abc.abstractclassmethod
    def next(self, servers: List[backend]) -> backend:
        """ Load in the data set"""
        raise NotImplementedError

def select_server(algo: Algo, servers: List[backend]) -> backend:
    return algo.next(servers)
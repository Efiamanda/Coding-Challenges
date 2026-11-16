from typing import List
from algo import Algo
from backend.backend import backend
from functools import reduce

class LeastConnection(Algo):
    def __init__(self):
        self.idx = 0

    def next(self, servers: List[backend]) -> backend | None:
        try: 
            choosen_server = None
            choosen_server = reduce(lambda x, y: x if x.num_connections < y.num_connections else y, servers)
            return choosen_server
        except:
            return None
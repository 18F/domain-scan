from abc import ABCMeta, abstractmethod
from typing import List


class Gatherer(metaclass=ABCMeta):

    def __init__(self, suffixes: List[str], options: dict, extra: dict={}):
        self.suffixes = suffixes
        self.options = options
        self.extra = extra

    @abstractmethod
    def gather(self):
        pass

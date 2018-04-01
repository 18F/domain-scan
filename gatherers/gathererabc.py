from abc import ABCMeta, abstractmethod
import os
from typing import List


class Gatherer(metaclass=ABCMeta):

    def __init__(self, suffixes: List[str], options: dict, extra: dict={}):
        self.suffixes = suffixes
        self.options = options
        self.extra = extra
        self.report_dir = self.options.get("output", "./")
        self.cache_dir = os.path.join(self.report_dir, "cache")
        self.results_dir = os.path.join(self.report_dir, "results")

    @abstractmethod
    def gather(self):
        pass

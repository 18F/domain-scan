from abc import ABCMeta, abstractmethod


class Gatherer(metaclass=ABCMeta):

    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def gather(self):
        pass

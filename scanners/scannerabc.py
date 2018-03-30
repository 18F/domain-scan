from abc import ABCMeta, abstractmethod
from typing import Type, TypeVar
import os

ScannerABCT = TypeVar("ScannerABCT")


class ScannerABC(metaclass=ABCMeta):

    def __init__(self, domain: str, handles: dict, environment: dict,
                 options: dict, extra: dict={}) -> None:
        self.domain = domain
        self.handles = handles
        self.environment = {**environment, **extra}
        self.options = options
        self.report_dir = self.options.get("output", "./")
        self.cache_dir = os.path.join(self.report_dir, "cache")
        self.results_dir = os.path.join(self.report_dir, "results")

        # Some subclasses may define an ``extra_environment`` property in their
        # __init__ methods, and we want to fold its values into the
        # ``environment`` property.
        self.environment.update(getattr(self, "extra_environment", {}))

    @abstractmethod
    def scan(self) -> dict:
        pass

    @abstractmethod
    def to_rows(self, data):
        pass

    @classmethod
    @abstractmethod
    def initialize_environment(cls: Type[ScannerABCT], environment: dict,
                               options: dict) -> dict:
        pass

    @property
    @abstractmethod
    def headers(self):
        # CSV headers for each row of data, e.g. ["Completed", "Constant", "Variable"]
        pass

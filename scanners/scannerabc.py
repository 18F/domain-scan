from abc import ABCMeta, abstractmethod
import os


class ScannerABC(metaclass=ABCMeta):

    lambda_support = False

    def __init__(self, environment: dict, options: dict) -> None:
        self.environment = environment
        self.options = options
        self.report_dir = self.options.get("output", "./")
        self.cache_dir = os.path.join(self.report_dir, "cache")
        self.results_dir = os.path.join(self.report_dir, "results")
        self.name = self.__class__.__module__.split(".")[-1]
        print(self.name)
        # If the scanner needs to set configuration elements, this should be
        # done in the subclass's __init__ method and stored in
        # self.initialized_opts.
        # This method should be called by the subclass's __init__ with:
        # super().__init__(environment, options)

    @abstractmethod
    def scan(self) -> dict:
        pass

    @abstractmethod
    def to_rows(self, data) -> list:
        pass

    @property
    @abstractmethod
    def headers(self):
        # CSV headers for each row of data, e.g. ["Completed", "Constant", "Variable"]
        pass

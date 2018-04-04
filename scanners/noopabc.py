import logging
from typing import List

from scanners.scannerabc import ScannerABC


###
# Testing scan class. Does nothing time consuming or destructive,
# but exercises many of the main hooks of domain-scan.
class Scanner(ScannerABC):

    # CSV headers for each row of data. Referenced locally.
    headers = ["Completed", "Constant", "Variable"]
    # Set a default number of workers for a particular scan type.
    # Overridden by a --workers flag.
    workers = 2  # type: int

    def __init__(self, environment: dict, options: dict) -> None:
        # The overall scanner options are set here.
        # Per-domain arguments should be passed to ``.scan()``.
        #
        # Run locally.
        logging.debug("Subclass (%s) __init__ method." % self.__module__)
        logging.debug("Initialize environment method.")
        self.initialized_opts = environment
        self.initialized_opts["constant"] = 12345
        super().__init__(environment, options)

    def scan(self, domain: str) -> dict:
        # Required scan function. This is the meat of the scanner, where things
        # that use the network or are otherwise expensive would go.
        #
        # Runs locally or in the cloud (Lambda).
        logging.debug("Scan function called with options: %s" % self.options)

        # Perform the "task".
        complete = True
        logging.warn("Complete!")

        return {
            'complete': complete,
            'constant': self.environment.get('constant'),
            'variable': self.environment.get('variable')
        }

    def to_rows(self, data) -> List[List[str]]:
        # CSV headers for each row of data, e.g.
        # ["Completed", "Constant", "Variable"]
        return [
            [data['complete'], data['constant'], data['variable']]
        ]

import logging
from typing import List, Type

from scanners.scannerabc import ScannerABC, ScannerABCT


###
# Testing scan class. Does nothing time consuming or destructive,
# but exercises many of the main hooks of domain-scan.
class Scanner(ScannerABC):

    # CSV headers for each row of data. Referenced locally.
    headers = ["Completed", "Constant", "Variable"]
    # Set a default number of workers for a particular scan type.
    # Overridden by a --workers flag.
    workers = 2  # type: int

    def __init__(self, domain: str, handles: dict, environment: dict,
                 options: dict, extra: dict={}) -> None:
        # Optional one-time initialization per-scan. If defined, any data
        # will be stored in the instance's ``extra_environment`` property.
        #
        # Run locally.
        logging.debug("Subclass (noopabc) __init__ method for %s." % domain)
        self.extra_environment = {"variable": domain}
        super().__init__(domain, handles, environment, options, extra)

    def scan(self) -> dict:
        # Required scan function. This is the meat of the scanner, where things
        # that use the network or are otherwise expensive would go.
        #
        # Runs locally or in the cloud (Lambda).
        domain = self.domain  # noqa
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

    @classmethod
    def initialize_environment(cls: Type[ScannerABCT], environment: dict,
                               options: dict) -> dict:
        # Optional one-time initialization for all scans.
        # If defined, any data returned will be passed to every scan instance.
        #
        # Run locally.
        logging.debug("Initialize environment method.")
        new_environment = {**environment}
        new_environment["constant"] = 12345
        return new_environment

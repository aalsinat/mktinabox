import logging
from ..handler import Handler


class CashlogyHandler(Handler):
    def __init__(self, successor=None, properties=None):
        Handler.__init__(self, successor=successor)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.properties = properties


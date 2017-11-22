import asyncore
import logging


class Dispatcher(asyncore.dispatcher):
    def __init__(self, sock=None, handlers=None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.handlers = handlers
        asyncore.dispatcher.__init__(self, sock=sock)

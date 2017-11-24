import asyncore
import logging


class Dispatcher(asyncore.dispatcher, object):
    def __init__(self, sock=None, handlers=None):
        super(Dispatcher, self).__init__(sock=sock)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.handlers = handlers

    def writable(self):
        return False

    def handle_close(self):
        self.logger.debug('handle_close()')
        self.close()

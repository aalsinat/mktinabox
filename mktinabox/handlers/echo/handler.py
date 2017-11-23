import logging
from reader.handlers.handler import Handler
from reader.dispatchers.dispatcher import Dispatcher


class Echo(Handler):
    def __init__(self, successor=None, properties=None):
        Handler.__init__(self, successor=successor)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.properties = properties

    def handle_request(self, **kwargs):
        data = kwargs.get('data', None)
        if data is not None:
            if self.properties is not None:
                filename = properties.get('filename')
                f = open(filename, 'w+')
                f.write(data)


class EchoHandler(Dispatcher):
    """
    Handles echoing messages from a single client.
    """

    def __init__(self, sock, printer, chunk_size=8192):
        self.chunk_size = chunk_size
        self.logger = logging.getLogger('EchoHandler%s' % str(sock.getsockname()))
        asyncore.dispatcher.__init__(self, sock=sock)
        self.data_to_write = None
        self.printer = printer
        return

    def handle_accept(self):
        # Called when a client connects to our socket
        client_info = self.accept()
        self.logger.debug('(%s) client_info %s', self.id, client_info)

    def writable(self):
        """We want to write if we have received data."""
        response = bool(self.data_to_write)
        self.logger.debug('(%s) writable() -> %s', self.id, response)
        return response

    def handle_write(self):
        """Write as much as possible of the most recent message we have received."""
        data = self.data_to_write.pop()
        sent = self.send(data[:self.chunk_size])
        if sent < len(data):
            remaining = data[sent:]
            self.data.to_write.append(remaining)
        self.logger.debug('(%s) handle_write() -> (%d) "%s"', self.id, sent, data[:sent])
        if not self.writable():
            self.handle_close()

    def handle_read(self):
        """Read an incoming message from the client and put it into our outgoing queue."""
        data = self.recv(self.chunk_size)
        self.logger.debug('(%s) handle_read() -> (%d) "%s"', self.id, len(data), data)
        self.data_to_write.insert(0, data)

    def handle_close(self):
        self.logger.debug('(%s) handle_close()', self.id)
        self.close()

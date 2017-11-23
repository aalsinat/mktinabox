"""
.. module:: reader
   :platform: Unix, Windows
   :synopsis: Main module for capturing receipts coming from POS systems.

.. moduleauthor:: Alex Alsina <alex.alsina@sikkurat.es>


"""
import asyncore
import socket
import sys
import threading
from conf import settings
from conf import settings
from dispatchers.cashlogy.dispatcher import Cashlogy
from dispatchers.dispatcher import Dispatcher
from handlers.echo.handler import Echo


class PrinterServer(Dispatcher, object):
    """
    Receives connections and establishes handlers for each client.
    """
    BACKLOG = 1

    def __init__(self, address, printer_name='TIQUETSMKT'):
        Dispatcher.__init__(self, sock=None)
        self.logger.debug('Initialize printer: %s', printer_name)
        if sys.platform == 'win32':
            from printer.win32 import Printer
            self.printer = Printer(printer_name)
            # init_cashlogy = threading.Thread(target=self.init_cashlogy, args=())
            # init_cashlogy.start()
        else:
            self.printer = None

        self.logger.debug('handle_accept() -> (%s, %s)', address[0], address[1])
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.bind(address)
        self.address = self.socket.getsockname()
        self.logger.debug('binding to %s', self.address)
        self.listen(PrinterServer.BACKLOG)

        # Initializing handlers
        handler = Echo(properties=settings.echo)
        self.logger.info('Echo handler created')

    def run(self):
        asyncore.loop()

    def writable(self):
        return False

    def readable(self):
        return self.accepting

    def handle_read(self):
        pass

    def handle_connect(self):
        pass

    def handle_close(self):
        self.logger.debug('handle_close()')
        self.close()
        return

    def handle_accept(self):
        """
        Manages all requests
        :return:
        """
        # Called when a client connects to our socket
        client_info = self.accept()
        self.logger.debug('handle_accept() -> %s', client_info[1])
        Cashlogy(sock=client_info[0], printer=self.printer)
        # EchoHandler(sock=client_info[0], printer=self.printer)
        # ICG(sock=client_info[0])
        # We only want to deal with one client at a time,
        # so close as soon as we set up the handler.
        # Normally you would not do this and the server
        # would run forever or until it received instructions
        # to stop.
        # self.handle_close()
        return

    def init_cashlogy(self):
        # Init Cashlogy connection
        self.logger.info('Initialize Cashlogy')
        hostname = settings.cashlogy['hostname']
        port = int(settings.cashlogy['port'])
        cashlogy_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.logger.info('Connecting to %s', (hostname, port))
        cashlogy_sock.connect((hostname, port))
        cashlogy_sock.send("#I,0#")
        data = cashlogy_sock.recv(128)
        self.logger.info('Cashlogy response %s', data)


def run(argv=None):
    """
    This method is the entry point of the ticket mktinabox.
    Creates a new instance of a `PrinterServer` and starts it.

    :param argv: Any list of parameters from the command line.

    """
    address = (settings.win32['inaddr'], int(settings.win32['inport']))
    server = PrinterServer(address, settings.win32['outprinter'])
    server.run()

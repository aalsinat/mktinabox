"""
.. module:: reader
   :platform: Unix, Windows
   :synopsis: Main module for capturing receipts coming from POS systems.

.. moduleauthor:: Alex Alsina <alex.alsina@sikkurat.es>


"""
import asyncore
import logging
import os
import socket
import sys

from mktinabox.conf import settings, BASE_DIR
from mktinabox.dispatchers import Dispatcher
from mktinabox.dispatchers.icg.dispatcher import ICG


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
        else:
            self.printer = None

        self.logger.debug('handle_accept() -> (%s, %s)', address[0], address[1])
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.bind(address)
        self.address = self.socket.getsockname()
        self.logger.debug('binding to %s', self.address)
        self.listen(PrinterServer.BACKLOG)

    def run(self, timeout=30.0, use_poll=False, map=None, count=None):
        """
        Enter a polling loop that terminates after count passes or all open channels have been closed. All arguments
        are optional. The count parameter defaults to None, resulting in the loop terminating only when all channels
        have been closed. The timeout argument sets the timeout parameter for the appropriate select() or poll()
        call, measured in seconds; the default is 30 seconds. The use_poll parameter, if true, indicates that poll()
        should be used in preference to select() (the default is False). The map parameter is a dictionary whose
        items are the channels to watch. As channels are closed they are deleted from their map. If map is omitted,
        a global map is used. Channels are instances of asyncore.dispatcher
        """
        asyncore.loop(timeout=timeout, use_poll=use_poll, map=map, count=None)

    def readable(self):
        return self.accepting

    def handle_read(self):
        pass

    def handle_connect(self):
        pass

    def handle_accept(self):
        """
        Manages all requests
        :return:
        """
        # Called when a client connects to our socket
        client_info = self.accept()
        self.logger.debug('handle_accept() -> %s', client_info[1])
        ICG(sock=client_info[0], printer=self.printer, chunk_size=2048)
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
    # Initialize log directory
    log_path = settings.log['path']
    log_filename = settings.log['name']
    directory = os.path.join(BASE_DIR, log_path)
    if not os.path.exists(directory):
        os.makedirs(directory)
    filename = os.path.join(directory, log_filename)

    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)-8s %(message)s', filename=filename)
    logger = logging.getLogger(__name__)
    logger.info("Current application path: %s", BASE_DIR)

    address = (settings.win32['inaddr'], int(settings.win32['inport']))
    server = PrinterServer(address, settings.win32['outprinter'])
    server.run()

import asyncore
import logging
import socket
import re
import os
from textx.metamodel import metamodel_from_file
from textx.exceptions import TextXError
import mktinabox.printer.win32
import time
import datetime
from escpos.printer import Dummy


class ICG(asyncore.dispatcher):
    """
    Handles echoing messages from a single client.
    """

    def __init__(self, sock, chunk_size=8192):
        self.chunk_size = chunk_size
        self.logger = logging.getLogger('ICGHandler%s' % str(sock.getsockname()))
        asyncore.dispatcher.__init__(self, sock=sock)
        self.data_to_write = None
        self.printer = mktinabox.printer.win32.Printer()
        self.logger.debug('Dummy printer init')
        self.dummy = Dummy()
        return

    def writable(self):
        """We want to write if we have received data."""
        response = bool(self.data_to_write)
        self.logger.debug('writable() -> %s', response)
        return False

    def handle_write(self):
        """Write as much as possible of the most recent message we have received."""
        self.logger.debug('handle_write() -> %s', self.data_to_write)
        if not self.writable():
            self.handle_close()

    def handle_read(self):
        """Read an incoming message from the client and put it into our outgoing queue."""
        data = self.recv(self.chunk_size)
        self.logger.debug('handle_read() -> (%d) "%s"', len(data), data)
        if (len(data) > 10):
            self.data_to_write = bytearray()
            self.data_to_write.extend(data)
            try:
                self.parse_ticket(self.remove_esc_pos(self.data_to_write))
            except TextXError as e:
                self.logger.error('Error parsing ticket: %s -> (line: %s, col: %s)', e.message, e.line, e.col)
                self.printer.DirectPrint('TIQUETSMKT', self.data_to_write)
                self.data_to_write = None
            else:
                self.data_to_write = self.remove_end_of_ticket(self.data_to_write)
                self.data_to_write.extend(self.dummy.output)
                self.printer.DirectPrint('TIQUETSMKT', self.data_to_write)
                self.data_to_write = None

    def handle_close(self):
        self.logger.debug('handle_close()')
        self.close()

    # Handler support methods

    def remove_end_of_ticket(self, ticket):
        out = re.sub(r"(\x1d\x56\x41).*$", '', ticket)
        return out

    def remove_esc_pos(self, ticket):
        # Delete ESC @ - Initialize printer
        out = re.sub(r"(\x1B\x40)", '', ticket)
        # Delete GS V - Select cut mode and cut paper
        out = re.sub(r"(\x1d\x56\x41).*$", '', out)
        # Delete ESC ! - Select print mode
        out = re.sub(r"(\x1B\x21).", '', out)
        # Delete CAN and ESC
        out = re.sub(r"(\x18|\x1B)", '', out)
        # Delete LF - Print and line feed
        # out = re.sub(r"(\x0A)", '', out)
        self.logger.debug('remove_esc_pos() -> %s', out)
        return out

    def parse_ticket(self, ticket):
        fileDir = r'c:\\temp'
        # fileDir = os.path.dirname(os.path.relpath('__file__'))
        filename = os.path.join(fileDir, 'icg.tx')
        meta_model = metamodel_from_file(filename, debug=False)
        obj_processor = {
            'Detail': self.detail_obj_processor
        }
        meta_model.register_obj_processors(obj_processor)
        model = meta_model.model_from_str(ticket.decode('Cp1252'), False)

    def detail_obj_processor(self, detail):
        self.dummy.control("CR")
        self.dummy.control("LF")

        self.dummy.set(align='center')
        self.dummy.text('Number of item lines: ')
        self.dummy.set(text_type='B')
        self.dummy.text(str(len(detail.items)))

        self.dummy.control("CR")
        self.dummy.control("LF")

        self.dummy.set(align='center')
        self.dummy.text('Means of payment lines: ')
        self.dummy.set(text_type='B')
        self.dummy.text(str(len(detail.means)))

        self.dummy.control("CR")
        self.dummy.control("LF")

        self.dummy.set(align='center')
        self.dummy.text('Example of barcode: ')
        self.dummy.control("CR")
        self.dummy.control("LF")

        self.dummy.barcode('12345678', 'EAN8')
        self.dummy.control("CR")
        self.dummy.control("LF")
        self.dummy.cut()

    def send_azkoyen_command(self, amount):
        # Init Cashlogy connection
        self.logger.debug('Connect Cashlogy')
        cashlogy_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cashlogy_sock.connect(('127.0.0.1', 8094))
        command = '#C,22#F001/66776#175#175#%s#' % amount.replace(',', '')
        self.logger.debug('send_azkoyen_command() -> %s', command)
        # Send command
        cashlogy_sock.send(command)
        data = cashlogy_sock.recv(128)
        self.logger.debug('send_azkoyen_command() -> Cashlogy response: %s', data)

# -*- coding: UTF-8 -*-
import os
import re
from datetime import datetime

from escpos.printer import Dummy
from textx.exceptions import TextXError
from win32print import WritePrinter, StartDocPrinter

from mktinabox.conf import settings, BASE_DIR
from mktinabox.grammar.grammar import Grammar
from mktinabox.printer import constants
from .. import Dispatcher

from mktinabox.handlers.qrsurvey import QRSurvey


class ICG(Dispatcher, object):
    """
    Handles echoing messages from a single client.
    """

    def __init__(self, printer, sock=None, chunk_size=8192):
        super(ICG, self).__init__(sock=sock)
        self.chunk_size = chunk_size
        self.data_to_write = None
        self.printer = printer
        self.dummy = None
        self.count = 0
        return

    def handle_read(self):
        """Read an incoming message from the client and put it into our outgoing queue."""
        data = self.recv(self.chunk_size)
        printer_name = settings.win32['outprinter']
        parse_ticket = eval(settings.grammar['parse'])
        self.logger.debug('handle_read() -> (%d) "%s"', len(data), data)
        # Should this condition be changed to detect special escape chains
        if len(data) > 10:
            self.data_to_write = bytearray()
            self.data_to_write.extend(data)
            try:
                self.log_ticket(self.data_to_write)
                if parse_ticket:
                    self.parse_ticket(self.remove_esc_pos(self.data_to_write))
            except TextXError as e:
                self.logger.error('Error parsing ticket: %s -> (line: %s, col: %s)', e.args, e.line, e.col)
                self.printer.direct_print(printer_name, self.data_to_write)
                self.data_to_write = None
            except ValueError as e:
                self.logger.error('Error parsing ticket: %s ', e)
                self.printer.direct_print(printer_name, self.data_to_write)
                self.data_to_write = None
            else:
                self.data_to_write = self.remove_end_of_ticket(self.data_to_write)
                #self.data_to_write.extend(self.dummy.output)
                self.data_to_write = b''.join([self.data_to_write, self.dummy.output])
                self.printer.direct_print(printer_name, self.data_to_write)
                self.log_ticket(self.data_to_write)
                self.data_to_write = None

    # Handler support methods

    def remove_end_of_ticket(self, ticket):
        out = re.sub(constants.CUT_PAPER(b'.'), b'', ticket)
        # out = re.sub(constants.HW_INIT, '', out)
        # out = re.sub(r"(\x1d\x56\x41).*$", '', ticket)
        return out

    def remove_esc_pos(self, ticket):
        # encoded_ticket = ticket.decode('cp1252').encode('ascii', 'replace')
        encoded_ticket = ticket.decode('iso-8859-15', 'replace').encode('ascii', 'replace')
        # ESC @ - Initialize printer
        init_printer = constants.HW_INIT
        # ESC ! - Select print mode
        select_mode = constants.SET_MODE(b'.')
        # ESC t n - Select character code table
        select_code_table = constants.SET_CODEPAGE(b'.')
        # GS V - Select cut mode and cut paper
        cut_mode = constants.CUT_PAPER(b'.')
        # ESC E - Text bold
        text_style = b'|'.join([constants.TXT_STYLE['bold'][True], constants.TXT_STYLE['bold'][False]])
        # GS ! - Text size
        text_size = constants.SET_SIZE(b'.')
        # ESC control character
        esc_char = constants.ESC
        # CAN control character
        can_char = constants.CAN
        # Regular expression for cleaning ESC/POS characters
        clean_expression = b'|'.join([init_printer, select_mode, select_code_table, cut_mode, text_style, text_size, can_char, esc_char])
        cleaned_ticket = re.sub(clean_expression, b'', encoded_ticket)
        # print 'remove_esc_pos() -> %s' % out
        return cleaned_ticket

    def _hasattr(self, model, attribute):
        return attribute in [attr for attr in dir(model) if not attr.startswith('__')]

    def log_ticket(self, ticket):
        if eval(settings.log['tickets']):
            tickets_path = settings.log['path']
            directory = os.path.join(BASE_DIR, tickets_path)
            if not os.path.exists(directory):
                os.makedirs(directory)
            filename = datetime.now().strftime('%Y%m%d-%H%M%S') + '.txt'
            file_path = os.path.normpath(os.path.join(directory, filename))
            f = open(file_path, 'wb+')
            f.write(ticket)

    def parse_ticket(self, ticket):
        parse_mode = eval(settings.grammar['debug'])
        filename = os.path.normpath(os.path.join(BASE_DIR, settings.grammar['path'], settings.grammar['name']))
        if os.path.isfile(filename):
            grammar = Grammar.from_file(filename)
            ticket_model = grammar.parse_from_string(ticket.decode('utf-8', 'replace'), parse_mode)
            self.logger.info('Ticket parsed successfully')
            # At this point we must decide how to call the chain of managers that are active.
            # We could consider that even the parsing of the ticket was considered as a handler.
            self.apply_handler(ticket_model)
        else:
            self.logger.error('########## Grammar file %s doesn\'t exists #############', filename)

    def apply_handler(self, receipt):
        self.dummy = QRSurvey().handle_request(receipt)
        self.dummy.cut()

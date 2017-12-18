import re
import os
from datetime import datetime

from textx.exceptions import TextXError
from escpos.printer import Dummy

from mktinabox.conf import settings, BASE_DIR
from mktinabox.grammar.grammar import Grammar
from mktinabox.printer import constants
from .. import Dispatcher


class ICG(Dispatcher, object):
    """
    Handles echoing messages from a single client.
    """

    def __init__(self, printer, sock=None, chunk_size=8192):
        super(ICG, self).__init__(sock=sock)
        self.chunk_size = chunk_size
        self.data_to_write = None
        self.printer = printer
        self.logger.debug('Dummy printer init')
        self.dummy = Dummy()
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
                self.logger.error('Error parsing ticket: %s -> (line: %s, col: %s)', e.message, e.line, e.col)
                self.printer.DirectPrint(printer_name, self.data_to_write)
                self.data_to_write = None
            else:
                # self.data_to_write = self.remove_end_of_ticket(self.data_to_write)
                self.data_to_write.extend(self.dummy.output)
                self.printer.DirectPrint(printer_name, self.data_to_write)
                self.data_to_write = None

    # Handler support methods

    def remove_end_of_ticket(self, ticket):
        out = re.sub(constants.PAPER_FULL_CUT_B, '', ticket)
        # out = re.sub(r"(\x1d\x56\x41).*$", '', ticket)
        return out

    def remove_esc_pos(self, ticket):
        # ESC @ - Initialize printer
        init_printer = constants.HW_INIT
        # ESC ! - Select print mode
        select_mode = constants.SET_MODE('.')
        # GS V - Select cut mode and cut paper
        cut_mode = constants.CUT_PAPER('.')
        # ESC E - Text bold
        text_style = '|'.join([constants.TXT_STYLE['bold'][True], constants.TXT_STYLE['bold'][False]])
        # GS ! - Text size
        text_size = constants.SET_SIZE('.')
        # ESC control character
        # esc_char = constants.ESC
        # CAN control character
        can_char = constants.CAN
        # Regular expression for cleaning ESC/POS characters
        clean_expression = '|'.join([init_printer, select_mode, cut_mode, text_style, text_size, can_char])
        out = re.sub(clean_expression, '', ticket)
        # print 'remove_esc_pos() -> %s' % out
        return out

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
            obj_processor = {
                'Detail': self.detail_obj_processor
            }
            grammar.register_obj_processor(obj_processor)
            ticket_ast = grammar.parse_from_string(ticket.decode('Cp1252').encode('ascii', 'replace'), parse_mode)
            self.logger.info('Ticket parsed successfully')
        else:
            self.logger.error('########## Grammar file %s doesn\'t exists #############', filename)

    def validate_rule_matching(self, model):
        self.logger.info('Parsed value for CompanyInfo')
        pass

    def detail_obj_processor(self, detail):
        self.dummy.control("CR")
        self.dummy.control("LF")

        self.dummy.set(align='center')
        self.dummy.text('Number of item lines: ')
        self.dummy.set(text_type='B')
        self.dummy.text(str(len(detail.receipt_items)))

        self.dummy.control("CR")
        self.dummy.control("LF")

        self.dummy.set(align='center')
        self.dummy.text('Means of payment lines: ')
        self.dummy.set(text_type='B')
        self.dummy.text(str(len(detail.payment.means)))

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

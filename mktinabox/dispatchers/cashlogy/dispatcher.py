import os
import re
from datetime import datetime

from escpos.printer import Dummy
from textx.exceptions import TextXError

from mktinabox.conf import settings, BASE_DIR
from mktinabox.grammar.grammar import Grammar
from mktinabox.printer import constants
from .api import CashlogyAPI, CashlogyResponse
from .. import Dispatcher


class Cashlogy(Dispatcher, object):
    """
    Handles echoing messages from a single client.
    """

    def __init__(self, printer, sock=None, chunk_size=8192):
        super(Cashlogy, self).__init__(sock=sock)
        self.chunk_size = chunk_size
        self.data_to_write = None
        self.printer = printer
        self.dummy = Dummy()
        self.print_ticket = True
        return

    def handle_read(self):
        """Read an incoming message from the client and put it into our outgoing queue."""
        data = self.recv(self.chunk_size)
        printer_name = settings.win32['outprinter']
        self.logger.debug('handle_read() -> (%d) "%s"', len(data), data)
        if len(data) > 10:
            self.data_to_write = bytearray()
            self.data_to_write.extend(data)
            try:
                self.log_ticket(self.data_to_write)
                self.parse_ticket(self.remove_esc_pos(self.data_to_write))
            except TextXError as e:
                self.logger.error('Error parsing ticket: %s -> (line: %s, col: %s)', e.message, e.line, e.col)
                if self.print_ticket:
                    self.printer.DirectPrint(printer_name, self.data_to_write)
                self.data_to_write = None
            else:
                if self.print_ticket:
                    self.data_to_write = self.remove_end_of_ticket(self.data_to_write)
                    self.data_to_write.extend(self.dummy.output)
                    self.printer.DirectPrint(printer_name, self.data_to_write)
                self.data_to_write = None

    def remove_end_of_ticket(self, ticket):
        out = re.sub(r"(\x1d\x56\x41).*$", '', ticket)
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
        # can_char = constants.CAN
        # Regular expression for cleaning ESC/POS characters
        clean_expression = '|'.join([init_printer, select_mode, cut_mode, text_style, text_size])
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
            f = open(file_path, 'w+')
            f.write(ticket)

    def parse_ticket(self, ticket):
        parse_mode = eval(settings.grammar['debug'])
        filename = os.path.normpath(os.path.join(BASE_DIR, settings.grammar['path'], settings.grammar['name']))
        if os.path.isfile(filename):
            grammar = Grammar.from_file(filename)
            ticket_lines = filter(lambda line: len(line.strip()) > 0, re.split(r'[\r\n]+', ticket.decode('Cp1252')))
            ticket_ast = filter(lambda model: model is not None,
                                [grammar.parse_from_string(line, parse_mode) for line in ticket_lines])
            # ticket_ast = filter(lambda model: model is not None, map(grammar.parse_from_string, ticket_lines))

            receipt_id = None
            till_ref = 'CashReference'
            cashier_name = 'CashierName'
            total_amount = None
            mean = None
            self.logger.info('----------------------')
            self.logger.info('Parsing ticket results')
            self.logger.info('----------------------')
            self.logger.info('Retrieved %d value(s) from ticket', len(ticket_ast))
            for model in ticket_ast:
                if self._hasattr(model, 'receipt_id'):
                    receipt_id = model.receipt_id
                    self.logger.info('Receipt identifier: %s', receipt_id)
                elif self._hasattr(model, 'cashier'):
                    cashier_name = model.cashier
                    self.logger.info('Cashier name: %s', cashier_name)
                elif self._hasattr(model, 'total_amount'):
                    total_amount = model.total_amount
                    self.logger.info('Total amount to be sent: %s', total_amount)
                elif self._hasattr(model, 'till_ref'):
                    till_ref = model.till_ref
                    self.logger.info('Till ref: %s', till_ref)
                elif self._hasattr(model, 'mean'):
                    mean = model.mean
                    self.logger.info('Mean of payment: %s', mean)
            self.logger.info('----------------------')

            if mean is not None:
                response = CashlogyResponse.from_string(CashlogyAPI.command_actions.PAYMENT,
                                                        CashlogyAPI.send_command(settings.cashlogy['hostname'],
                                                                                 int(settings.cashlogy['port']),
                                                                                 CashlogyAPI.create_command(
                                                                                     [('action',
                                                                                       CashlogyAPI.command_actions.PAYMENT),
                                                                                      ('receipt_ref', receipt_id),
                                                                                      ('till_ref', till_ref),
                                                                                      ('cashier_name', cashier_name),
                                                                                      ('total_amount',
                                                                                       total_amount.replace(',', ''))])))
                self.print_ticket = bool(int(response.params['print_ticket']))
                if self.print_ticket:
                    self.logger.info('*** Cashlogy sets that receipt MUST be printed ***')
                else:
                    self.logger.info('*** Cashlogy sets that receipt MUST NOT be printed ***')
                if response.status == CashlogyAPI.response_status.OK or response.status == CashlogyAPI.response_status.WARNING:
                    automatic_cashed = round(float(response.params['automatic_cashed']) / 100, 2)
                    manual_cashed = round(float(response.params['manual_cashed']) / 100, 2)
                    given = '{:03.2f}'.format(automatic_cashed + manual_cashed)
                    exchange = '{:03.2f}'.format(round(float(response.params['exchange']) / 100, 2))
                    self.detail_obj_processor(given, exchange)
        else:
            self.logger.error('########## Grammar file %s doesn\'t exists #############', filename)

    def detail_obj_processor(self, given, exchange):
        self.dummy.control('LF')
        self.dummy.control('CR')
        self.dummy.set(align='center')
        self.dummy.text('ENTREGADO: ')
        self.dummy.set(text_type='B')
        self.dummy.text(given)
        self.dummy.control('LF')
        self.dummy.control('CR')
        self.dummy.set(align='center')
        self.dummy.text(' - CAMBIO: ')
        self.dummy.set(text_type='B')
        self.dummy.text(exchange)
        self.dummy.cut()

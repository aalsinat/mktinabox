import socket

import os
import re
from escpos.printer import Dummy
from textx.exceptions import TextXError

from reader.grammar.grammar import Grammar
from reader.handlers import constants
from reader.dispatchers.dispatcher import Dispatcher
from reader.conf import settings, BASE_DIR


class Cashlogy(Dispatcher):
    """
    Handles echoing messages from a single client.
    """

    def __init__(self, printer, sock=None, chunk_size=8192):
        Dispatcher.__init__(self, sock=sock)
        self.chunk_size = chunk_size
        self.data_to_write = None
        self.printer = printer
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
        printer_name = settings.win32['outprinter']
        self.logger.debug('handle_read() -> (%d) "%s"', len(data), data)
        if len(data) > 10:
            self.data_to_write = bytearray()
            self.data_to_write.extend(data)
            try:
                self.parse_ticket(self.remove_esc_pos(self.data_to_write))
            except TextXError as e:
                self.logger.error('Error parsing ticket: %s -> (line: %s, col: %s)', e.message, e.line, e.col)
                self.printer.DirectPrint(printer_name, self.data_to_write)
                self.data_to_write = None
            else:
                self.data_to_write = self.remove_end_of_ticket(self.data_to_write)
                self.data_to_write.extend(self.dummy.output)
                self.printer.DirectPrint(printer_name, self.data_to_write)
                self.data_to_write = None

    def handle_close(self):
        self.logger.debug('handle_close()')
        self.close()

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

    def parse_ticket(self, ticket):
        parse_mode = bool(settings.grammar['debug'])
        filename = os.path.normpath(os.path.join(BASE_DIR, settings.grammar['path'], settings.grammar['name']))
        grammar = Grammar.from_file(filename)
        ticket_lines = filter(lambda line: len(line.strip()) > 0, re.split(r'[\r\n]+', ticket.decode('Cp1252')))
        ticket_ast = filter(lambda model: model is not None,
                            [grammar.parse_from_string(line, parse_mode) for line in ticket_lines])
        # ticket_ast = filter(lambda model: model is not None, map(grammar.parse_from_string, ticket_lines))
        self.logger.info('Instantiated models %d', len(ticket_ast))

        ticket_id = None
        cash_code = 'Cash1'
        username = 'Username'
        amount = None
        payment_method = None
        for model in ticket_ast:
            if self._hasattr(model, 'id'):
                ticket_id = model.id
            elif self._hasattr(model, 'user'):
                username = model.user
            elif self._hasattr(model, 'amount'):
                amount = model.amount
            elif self._hasattr(model, 'cashcode'):
                cash_code = model.cashcode
            elif self._hasattr(model, 'method'):
                payment_method = model.method

        if payment_method is not None:
            self.sync_with_cashlogy(ticket_id, amount, user=username, cash_code=cash_code)

    def sync_with_cashlogy(self, ticket_id, amount, cash_code='Cash1', user='Username'):
        self.logger.info('sync_with_cashlogy() -> <type: Efectivo | amount: %s>', amount)
        response = self.send_azkoyen_command(ticket_id, amount, cash_code=cash_code, user=user)
        accounting = response.split('#')
        if len(accounting) == 8:
            given_amount = '{:03.2f}'.format(round(float(accounting[5]) / 100, 2))
            exchange_amount = '{:03.2f}'.format(round(float(accounting[4]) / 100, 2))
            self.detail_obj_processor(given_amount, exchange_amount)

    # def means_of_payment_obj_processor(self, means_of_payment):
    #     self.logger.debug('means_of_payment_processor() -> <type: %s | amount: %s>',
    #                       means_of_payment.type,
    #                       means_of_payment.amount)
    #     # Response exemple: #WR:LEVEL,22#F001/66776#0#300#500#0#
    #     response = self.send_azkoyen_command(means_of_payment.amount)
    #     accounting = response.split('#')
    #     if len(accounting) == 8:
    #         given_amount = '{:03.2f}'.format(round(float(accounting[5])/100, 2))
    #         exchange_amount = '{:03.2f}'.format(round(float(accounting[4])/100, 2))
    #         self.detail_obj_processor(given_amount, exchange_amount)

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

    def send_azkoyen_command(self, ticket_id, amount, cash_code='Cash', user='Username'):
        # Init Cashlogy connection
        self.logger.info('Connect Cashlogy')
        hostname = settings.cashlogy['hostname']
        port = int(settings.cashlogy['port'])
        cashlogy_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cashlogy_sock.connect((hostname, port))
        params = '#'.join([str(ticket_id), cash_code, user, amount.replace(',', '')])
        command = '#C,%d#%s#' % (len(params), params)
        self.logger.info('send_azkoyen_command() -> %s', command)
        # Send command
        cashlogy_sock.send(command)
        data = cashlogy_sock.recv(128)
        self.logger.info('send_azkoyen_command() -> Cashlogy response: %s', data)
        return data

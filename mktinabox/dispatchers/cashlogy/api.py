import logging
import socket
from collections import OrderedDict

from mktinabox.utils import enum


class CashlogyAPI(object):
    """
    This class will offer a set of methods to integrate with Cashlogy.
    Once transaction data has been captured from the POS (ticket capture)
    it can be sent to CashlogyTickets using its interface commands.
    Before sending commands an initialisation sequence must be executed.
    """
    command_actions = enum(INITIALIZE='I', FINISH='E', PAYMENT='C', REFUND='P', CANCEL='!', RESET='Z')
    response_status = enum(OK='0', WARNING='WR', ERROR='ER')
    response_definition = {
        command_actions.INITIALIZE: [],
        command_actions.FINISH: [],
        command_actions.PAYMENT: ['receipt_ref',
                                  'automatic_cashed',
                                  'exchange',
                                  'manual_cashed',
                                  'changes',
                                  'print_ticket'],
        command_actions.REFUND: ['refund_ref',
                                 'receipt_ref',
                                 'exchange',
                                 'changes',
                                 'print_ticket'],
        command_actions.CANCEL: [],
        command_actions.RESET: [],
    }

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

        pass

    @staticmethod
    def create_command(*args, **params):
        return CashlogyCommand(*args, **params)

    @staticmethod
    def initialize(hostname, port):
        CashlogyResponse.from_string(CashlogyAPI.command_actions.INITIALIZE,
                                     CashlogyAPI.send_command(hostname, port,
                                                              CashlogyAPI.create_command(
                                                                  [(
                                                                   'action', CashlogyAPI.command_actions.INITIALIZE)])))

    @staticmethod
    def send_command(hostname, port, cashlogy_command):
        # Init Cashlogy connection
        cashlogy_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cashlogy_sock.connect((hostname, port))
        # Send command
        cashlogy_sock.send(str(cashlogy_command))
        return cashlogy_sock.recv(128)


class CashlogyCommand(object):
    def __init__(self, *args, **params):
        self.params = OrderedDict(*args, **params)
        self.action = self.params.pop('action', None)

    def __getitem__(self, item):
        return getattr(self, item)

    def __repr__(self):
        params = '#'.join(list(self.params.values()))
        command = '#%s,%d#%s#' % (self.action, len(params), params) if len(params) > 0 else '#%s,%d#' % (self.action, 0)
        return command

    __str__ = __repr__


class CashlogyResponse(object):
    def __init__(self, action, status, iterable=(), **params):
        self.action = action
        self.status = status
        self.params = OrderedDict(iterable, **params)

    @classmethod
    def from_string(cls, action, response):
        items = response.split('#')
        response_status = items[1].split(',')
        status = response_status[0].split(':')
        expected = zip(CashlogyAPI.response_definition[action], items[2:])
        return cls(action, status[0], expected)

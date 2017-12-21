"""
Avoid coupling the sender of a request to its receiver by giving
more than one object a chance to handle the request. Chain the receiving
objects and pass the request along the chain until an object handles it.
"""
import logging
from mktinabox.core.exceptions import MethodNotImplemented


class Handler(object):
    """
    Define an interface for handling requests.
    Implement the successor link.
    """

    def __init__(self, iterable=(), **properties):
        """
        In the constructor method we will pass all the options defined in the properties file.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.__dict__.update(iterable, **properties)
        self.__successor = None

    @property
    def successor(self):
        return self.__successor

    @successor.setter
    def successor(self, successor):
        self.__successor = successor

    def handle_request(self, **kwargs):
        """Abstract method: Handle request, otherwise forward it to the successor."""
        raise MethodNotImplemented("Method handle_request must be implemented.")

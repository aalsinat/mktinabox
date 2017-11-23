"""
Avoid coupling the sender of a request to its receiver by giving
more than one object a chance to handle the request. Chain the receiving
objects and pass the request along the chain until an object handles it.
"""


class Handler(object):
    """
    Define an interface for handling requests.
    Implement the successor link.
    """

    def __init__(self, successor=None):
        self._successor = successor

    def handle_request(self, **kwargs):
        """Abstract method: Handle request, otherwise forward it to the successor."""
        pass

from conf import settings
from reader import PrinterServer

__all__ = ["PrinterServer", "run"]

def run(argv=None):
    address = (settings.win32['inaddr'], int(settings.win32['inport']))
    server = PrinterServer(address, settings.win32['outprinter'])
    server.run()

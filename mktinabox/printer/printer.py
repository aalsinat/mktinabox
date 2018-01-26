import time
import win32print


class Printer:
    def __init__(self, prtname=None):
        if prtname == None:
            self.prtname = win32print.GetDefaultPrinter()
        else:
            self.prtname = prtname

    def direct_print(self, prtname, data):
        printer = win32print.OpenPrinter(prtname)
        if printer:
            time.sleep(.1)
            try:
                job = win32print.StartDocPrinter(printer, 1, ('MktReceipt', None, 'RAW'))
                try:
                    win32print.StartPagePrinter(printer)
                    win32print.WritePrinter(printer, data)
                    win32print.EndPagePrinter(printer)
                finally:
                    win32print.EndDocPrinter(printer)
            finally:
                win32print.ClosePrinter(printer)

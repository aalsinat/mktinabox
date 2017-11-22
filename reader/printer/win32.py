import time
import ctypes
import ctypes.wintypes

LPTSTR = ctypes.c_char_p


class DOCINFO_1(ctypes.Structure):
    _fields_ = [
        ("pDocName", LPTSTR),
        ("pOutputFile", LPTSTR),
        ("pDataType", LPTSTR),
    ]

class Printer:
    def __init__(self, prtname=None):
        self.winspool = ctypes.WinDLL("Winspool.drv")
        if prtname == None:
            self.prtname = self.get_default_printer
        else:
            self.prtname = prtname

    def get_default_printer(self):
        """
        Gets system default printer
        :return: printer name
        """
        # -- Get the default printer
        plen = ctypes.c_long()
        ret = self.winspool.GetDefaultPrinterA(None, ctypes.byref(plen))
        pname = ctypes.c_buffer(plen.value)
        ret = self.winspool.GetDefaultPrinterA(pname, ctypes.byref(plen))
        return pname.value

    def OpenPrinter(self, prtname=None):
        # -- Let open our printer
        if prtname == None:
            pass
        else:
            self.prtname = prtname
        self.handle = ctypes.c_ulong()
        ret = self.winspool.OpenPrinterA(self.prtname, ctypes.byref(self.handle), None)
        return self.handle

    def ClosePrinter(self, handle=None):
        # -- Close our printer after opening it
        if handle == None:
            self.winspool.ClosePrinter(self.handle)
            self.handle = None
        else:
            self.winspool.ClosePrinter(handle)
            handle = None

            # StartDocPrinter(ByVal hPrinter As IntPtr, ByVal Level As Integer, ByRef pDocInfo As DOCINFO) As Long

    def StartDocPrinter(self):
        pDocInfo = DOCINFO_1()  # ctypes.cast(Printer, ctypes.POINTER(DOCINFO_1))
        pDocInfo.pDocName = "mktinaboxTiquet"
        pDocInfo.pDataType = "RAW"
        # ret=self.winspool.StartDocPrinterW(self.handle, 1, ctypes.POINTER(pDocInfo)) # pDocInfo.ptr)
        return self.winspool.StartDocPrinterA(self.handle, 1, ctypes.byref(pDocInfo))

    #        Printer=(ctypes.c_ubyte*dwNeeded.value)()
    #        ctypes.StructType(
    #        "docInfo1",
    #        [
    #            {pDocName: ctypes.jschar.ptr},
    #            {pOutputFile: ctypes.voidptr_t},
    #            {pDataType: ctypes.voidptr_t},
    #        ]

    def EndDocPrinter(self):
        return self.winspool.EndDocPrinter(self.handle)

    def StartPagePrinter(self):
        return self.winspool.StartPagePrinter(self.handle)

    def EndPagePrinter(self):
        return self.winspool.EndPagePrinter(self.handle)

    def WritePrinter(self, data):
        # WritePrinter(ByVal hPrinter As IntPtr, ByVal data As String, ByVal buf As Integer, ByRef pcWritten As Integer) As Long
        dwWritten = ctypes.wintypes.DWORD()
        return self.winspool.WritePrinter(self.handle, ctypes.c_char_p(str(data)), ctypes.wintypes.DWORD(len(data)),
                                          ctypes.byref(dwWritten))
        # return self.winspool.WritePrinter(self.handle, ctypes.byref(data),ctypes.wintypes.DWORD(Len(lsBytes)),ctypes.byref(data))
        # return self.winspool.WritePrinter(self.handle, ctypes.c_char_p(data),ctypes.wintypes.DWORD(Len(lsBytes)))
        # .WritePrinter (hPrinter, raw_data)

    def DirectPrint(self, psPrinter, psData):
        if self.OpenPrinter(psPrinter):
            time.sleep(.1)
            if self.StartDocPrinter():
                time.sleep(.1)
                if self.StartPagePrinter():
                    time.sleep(.1)
                    #                    sts=self.WritePrinter(psData)
                    #                    if sts:
                    #                        print "print win32 OK!"
                    #                        pass
                    #                    else:
                    #                        print "Error WritePrinter"
                    lnBufferMax = 4096
                    lnBufferWait = .3
                    lnN = 0
                    bchunks = [psData[i:i + lnBufferMax] for i in range(0, len(psData), lnBufferMax)]
                    for bchunk in bchunks:
                        if lnN > 0:
                            time.sleep(lnBufferWait)
                        sts = self.WritePrinter(bchunk)
                        if sts:
                            print "print win32 OK!"
                            pass
                        else:
                            print "Error WritePrinter chunk [%s]" % (lnN)
                        lnN = lnN + 1
                    time.sleep(.1)
                    self.EndPagePrinter()
                else:
                    print "Error startpageprinter"
                self.EndDocPrinter()
            else:
                print "Error StarDocPrinter"
            self.ClosePrinter()
        else:
            print "Error openprinter"

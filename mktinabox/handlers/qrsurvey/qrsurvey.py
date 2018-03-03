# -*- coding: UTF-8 -*-
import locale
import os

from escpos.constants import ESC
from escpos.printer import Dummy

from mktinabox.conf import settings, BASE_DIR
from mktinabox.handlers import Handler
from mktinabox.utils.encoding import Encoding


class QRSurvey(Handler):
    def __init__(self, iterable=(), **properties):
        """
        In the constructor method we will pass all the options defined in the properties file.
        """
        super(QRSurvey, self).__init__(iterable, **properties)
        self.__dummy = None
        locale.setlocale(locale.LC_NUMERIC, settings.sys['locale'])

    def handle_request(self, ticket_model):
        """ This method receives the receipt model created from parsing according to the rules of a grammar. Returns
        the part of the posticket to be printed. """
        if not self.__meet_lower_limit(ticket_model, settings.qrsurvey['limit'].strip()) or self.__is_refund(
                ticket_model) or self.__meet_total_discount(ticket_model) or self.__meet_means_of_payment(ticket_model):
            return Dummy()
        return self.__print(ticket_model)

    def __meet_lower_limit(self, ticket, limit):
        return locale.atof(ticket.taxes.total.amount.strip()) > locale.atof(limit)

    def __is_refund(self, ticket):
        return ticket.footer.refund is not None

    def __meet_total_discount(self, ticket):
        meets = False
        black_list = map(lambda x: int(x.strip()), settings.qrsurvey['discounts'].split('|'))

        for discount in ticket.detail.discounts:
            is_on_the_list = [index for index, forbidden in enumerate(black_list) if
                              forbidden == int(discount.discount_id.strip())]
            if len(is_on_the_list) > 0:
                meets = True
        return meets

    def __meet_means_of_payment(self, ticket):
        meets = False
        black_list = map(lambda x: x.upper(), settings.qrsurvey['means'].split('|'))

        for mean in ticket.means.payment.means:
            is_on_the_list = [index for index, forbidden in enumerate(black_list) if
                              forbidden == mean.description.strip().upper()]
            if len(is_on_the_list) > 0:
                meets = True
        return meets

    def __print(self, ticket):
        self.__dummy = Dummy()
        self.__dummy.charcode('MULTILINGUAL')

        path = os.path.normpath(os.path.join(BASE_DIR, './mktinabox/handlers/qrsurvey/caritas1apx.png'))
        self.__dummy.set(align='center')

        self.__dummy.image(path, impl='graphics')
        self.__dummy.control('CR')
        self.__dummy.control('LF')

        languages = settings.qrsurvey['lang'].split('|')

        self.__dummy.set(align='center', height=2)
        for lang in languages:
            self.__dummy.text(settings.qrsurvey['message.' + lang])
            # self.__dummy.text(Encoding.decode(settings.qrsurvey['message.' + lang]))
            self.__dummy.control('CR')
            self.__dummy.control('LF')

        self.__dummy.control('CR')
        self.__dummy.control('LF')

        qrtext = settings.qrsurvey['urlqr'].format(cod_cve=settings.sys['cod_cve'].strip(),
                                                   serial_number=ticket.header.receipt_info.receipt_id.header_serial_number.strip(),
                                                   document_number=ticket.header.receipt_info.receipt_id.document_number.strip(),
                                                   tpv=settings.sys['tpv'].strip())
        urltext = settings.qrsurvey['urltext'].format(cod_cve=settings.sys['cod_cve'].strip())

        self.__dummy.qr(content=qrtext, size=6, native=True)
        self.__dummy.control('CR')
        self.__dummy.control('LF')

        # for lang in languages:
        #     self.__dummy.text(settings.qrsurvey['footer.' + lang].decode('cp1252'))
        #     self.__dummy.control('CR')
        #     self.__dummy.control('LF')

        self.__dummy._raw(ESC + b'!\x01')
        urltexy = r''
        self.__dummy.text(urltext)
        self.__dummy.control('CR')
        self.__dummy.control('LF')

        self.__dummy._raw(ESC + b'!\x01')
        for lang in languages:
            self.__dummy.text(settings.qrsurvey['legal.' + lang])
            # self.__dummy.text(Encoding.decode(settings.qrsurvey['legal.' + lang]).decode('cp850'))
            self.__dummy.control('CR')
            self.__dummy.control('LF')

        return self.__dummy

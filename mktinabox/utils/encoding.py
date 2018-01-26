import re
import binascii


class Encoding(object):
    @staticmethod
    def encode(raw_string, mask=False):
        result = ''.join(
            [c if c in b' /-|,.01234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ' else "\\x%02X" % ord(
                c) for
             c in str(raw_string)])
        if mask:
            #result = "b'{0}'".format(result)
            result = "b'" + result + "'"
        return result

    @staticmethod
    def __ascii_replace(match):
        s = match.group()
        return binascii.unhexlify(s[2:]).decode()

    @staticmethod
    def decode(input_string):
        pattern = re.compile(r'\\x(\w{2})')
        return pattern.sub(Encoding.__ascii_replace, input_string)

import logging
import os
import sys

from mktinabox.server import run

if __name__ == '__main__':
    os.environ.setdefault('READER_SETTINGS', 'properties.ini')

    run(sys.argv)

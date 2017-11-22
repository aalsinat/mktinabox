import logging
import os
import sys

from reader import run

if __name__ == '__main__':
    os.environ.setdefault('READER_SETTINGS', 'properties.ini')

    logging.basicConfig(level=logging.INFO, format='%(name)s: %(message)s')
    logger = logging.getLogger('Mktinabox')

    run(sys.argv)

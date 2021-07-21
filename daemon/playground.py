from pprint import pprint
from pluggram import load
import logging

logging.basicConfig(level=logging.DEBUG,
                    format='[%(levelname)s][%(module)s:%(lineno)s]: %(message)s')

pluggrams = load('programs')
pprint(pluggrams)

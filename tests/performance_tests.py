# -*- coding: utf-8 -*-

"""
Simple performance indicator for HipChatParser

Seconds take to parse 5000 messages:
Naive implementation - 0.766
Compiled regex - 0.676
"""

import sys
sys.path.append('..\\hipchatparser')

import timeit
from hipchatparser import HipChatParser
from tests.test_hipchatparser import FakeUrlFetcher

def main():

    parser = HipChatParser(url_fetcher=FakeUrlFetcher({}))
    strings = [
        'String with any matching features but that is somewhat long)',
        'Good morning! (megusta) (coffee)',
        'Good morning! (thisIsTooLongToBeAnEmoticon)',
        'Olympics are starting soon; http://www.nbcolympics.com',
        '@bob @john (success) such a cool feature; https://twitter.com/jdorfman/status/430511497475670016'
    ]

    executor = lambda: all(parser.parse(x) is not None for x in strings)
    print timeit.timeit(executor, number=1000)

if __name__ == '__main__':
    main()
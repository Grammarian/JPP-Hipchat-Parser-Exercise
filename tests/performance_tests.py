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


class PerformanceStatistician:
    """
    This class keeps track of performance measurements and calculates some simple stats
    """
    def __init__(self):
        self._measurements = list()

    def measure(self, func, iterations=1):
        """
        Measure how long the given func takes, and add it to our list of measurements
        """
        duration = timeit.timeit(func, number=iterations)
        self.add(duration)

    def add(self, measurement):
        """
        Add a performance measurement (in seconds) to the collection to be reported on.
        """
        self._measurements.append(measurement)

    def report(self):
        """
        Returns string representing some stats about the measurements
        """
        d = {
            'count': len(self._measurements),
            'min': min(self._measurements),
            'max': max(self._measurements),
            'avg': sum(self._measurements) / len(self._measurements),
            'median': (min(self._measurements) + max(self._measurements)) / 2  # technical -- not the median, I know
        }
        return """Performance stats ({count} measurements):
- Minimum: {min:f}
- Maximum: {max:f}
- Average: {avg:f}
- Median: {mean:f}""".format(**d)


def test1(strings):
    parser = HipChatParser(url_fetcher=FakeUrlFetcher({}))
    iterations = 1000
    executor = lambda: all(parser.parse(x) is not None for x in strings)
    print '{} messages: {:f} seconds'.format(len(strings) * iterations, timeit.timeit(executor, number=iterations))


def test2(strings):
    parser = HipChatParser(url_fetcher=FakeUrlFetcher({}))
    stats = PerformanceStatistician()
    for x in strings:
        stats.measure(lambda: parser.parse(x))
    print stats.report()


def main():
    strings = [
        'String with any matching features but that is somewhat long)',
        'Good morning! (megusta) (coffee)',
        'Good morning! (thisIsTooLongToBeAnEmoticon)',
        '@bob @john (success) such a cool feature; https://twitter.com/jdorfman/status/430511497475670016',
        'morning @moe, morning @curly',
        'morning @larry (sunrise)',
        'i saw something fascinating last night',
        '@abbott @costelloa (thumbsup) https://www.youtube.com/watch?v=kTcRRaXV-fg',
        'you can read all about the history here https://en.wikipedia.org/wiki/Who%27s_on_First%3F',
        "don't you think that's just so funny? (rotfl)",
    ]
    test1(strings)
    test2(strings)

if __name__ == '__main__':
    main()
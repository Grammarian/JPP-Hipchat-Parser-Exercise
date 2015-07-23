#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from hipchatparser import HipChatParser

class FakeUrlFetcher:
    """
    This class is a facade for fetching the contents of a URL.

    It allows us to play with different implementations (urllib2 vs Requests),
    as well as mock out the actual GET during unit tests
    """

    def __init__(self, d = None):
        self._dict = d if d is not None else { }

    def get(self, url):
        """
        Fetch the contents of the given URL.

        If the given url can be fetched within a sensible amount of time,
        return an empty string.
        """
        return self._dict.get(url, url)


class TestHipchatparser(unittest.TestCase):
    def setUp(self):
        pass

    def test_Parse_None_EmptyJsonString(self):
        p = HipChatParser()
        s = None
        self.assertEqual(p.parse(s), '{}')

    def test_Parse_EmptyString_EmptyJsonString(self):
        p = HipChatParser()
        s = ''
        self.assertEqual(p.parse(s), '{}')

    def test_Parse_StringWithoutAnyMarkup_EmptyJsonString(self):
        p = HipChatParser()
        s = 'this string contains no interesting markup'
        self.assertEqual(p.parse(s), '{}')

    def test_Parse_Mentions_BareAt_EmptyJsonString(self):
        p = HipChatParser()
        s = 'this string contains a lonely @ sign'
        self.assertEqual(p.parse(s), '{}')

    def test_Parse_Mentions_Single(self):
        p = HipChatParser()
        s = '@chris you around?'
        t = ('{\n'
             '  "mentions": [\n'
             '    "chris"\n'
             '  ]\n'
             '}')
        self.assertEqual(p.parse(s), t)

    def test_Parse_Mentions_Single_AtEnd(self):
        p = HipChatParser()
        s = 'you around? @chris'
        t = ('{\n'
             '  "mentions": [\n'
             '    "chris"\n'
             '  ]\n'
             '}')
        self.assertEqual(p.parse(s), t)

    def test_Parse_Emoticons_UnmatchedBrackets_EmptyJsonString(self):
        p = HipChatParser()
        s = 'Good morning! (megusta coffee)'
        t = '{}'
        self.assertEqual(p.parse(s), t)

    def test_Parse_Emoticons_TooLongIdentifier_EmptyJsonString(self):
        p = HipChatParser()
        s = 'Good morning! (thisIsTooLongToBeAnEmoticon)'
        t = '{}'
        self.assertEqual(p.parse(s), t)

    def test_Parse_Emoticons_Multiple(self):
        p = HipChatParser()
        s = 'Good morning! (megusta) (coffee)'
        t = ('{\n'
             '  "emoticons": [\n'
             '    "megusta", \n'
             '    "coffee"\n'
             '  ]\n'
             '}')
        self.assertEqual(p.parse(s), t)

    def test_Parse_Links_Single(self):
        fake_url_fetcher = FakeUrlFetcher({
            "http://www.nbcolympics.com": "<title>NBC Olympics | 2014 NBC Olympics in Sochi Russia</title>"})
        p = HipChatParser(url_fetcher=fake_url_fetcher)
        s = 'Olympics are starting soon; http://www.nbcolympics.com'
        t = ('{\n'
             '  "links": [\n'
             '    {\n'
             '      "title": "NBC Olympics | 2014 NBC Olympics in Sochi Russia", \n'
             '      "url": "http://www.nbcolympics.com"\n'
             '    }\n'
             '  ]\n'
             '}')
        self.assertEqual(p.parse(s), t)

    def test_Parse_Everything(self):
        fake_url_fetcher = FakeUrlFetcher({
            "https://twitter.com/jdorfman/status/430511497475670016":
                "<title>Justin Dorfman on Twitter: &quot;nice @littlebigdetail from @HipChat (shows hex "
                "colors when pasted in chat). http://t.co/7cI6Gjy5pq&quot;</title>"})
        p = HipChatParser(url_fetcher=fake_url_fetcher)
        s = '@bob @john (success) such a cool feature; https://twitter.com/jdorfman/status/430511497475670016'
        t = ('{\n'
             '  "emoticons": [\n'
             '    "success"\n'
             '  ], \n'
             '  "links": [\n'
             '    {\n'
             '      "title": "Justin Dorfman on Twitter: \\\"nice @littlebigdetail from @HipChat (shows hex '
             'colors when pasted in chat). http://t.co/7cI6Gjy5pq\\\"\", \n'
             '      "url": "https://twitter.com/jdorfman/status/430511497475670016"\n'
             '    }\n'
             '  ], \n'
             '  "mentions": [\n'
             '    "bob", \n'
             '    "john"\n'
             '  ]\n'
             '}')
        self.assertMultiLineEqual(p.parse(s), t)

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()

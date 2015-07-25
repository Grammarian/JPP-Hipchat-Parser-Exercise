# -*- coding: utf-8 -*-

import HTMLParser
import json
import re
import urllib2
import time


class HipChatParser:
    """
    This class implements are simple message parsing scheme to extract details from given messages.
    These details are returned as a JSON string.

    Special content to look for includes:

    1. @mentions - A way to mention a user. Always starts with an '@' and ends when hitting a non-word character.
       :ref:`http://help.hipchat.com/knowledgebase/articles/64429-how-do-mentions-work-`

    2. Emoticons - Emoticons are alphanumeric strings, no longer than 15 characters, contained in parenthesis.
       :ref:`https://www.hipchat.com/emoticons`

    3. Links - Any URLs contained in the message, along with the page's title.
    """

    DETAIL_MENTIONS = "mentions"
    DETAIL_EMOTICONS = "emoticons"
    DETAIL_LINKS = "links"
    DETAIL_URL = "url"
    DETAIL_TITLE = "title"

    # Pre-compile regex's for slight performance boost
    # Regex to extract URL from: http://stackoverflow.com/questions/6883049/regex-to-find-urls-in-string-in-python
    _re_emoticon = re.compile('\([0-9a-zA-Z]{1,15}\)')
    _re_mentions = re.compile('@\w+')
    _re_title = re.compile('<title>(.*)</title>', re.IGNORECASE)
    _re_url = re.compile('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')

    def __init__(self, url_fetcher=None, *args, **kwargs):
        """
        Create a new HipChatParser
        """
        self._url_fetcher = url_fetcher if url_fetcher is not None else UrlFetcher()
        self._html_parser = HTMLParser.HTMLParser()

    def parse(self, message):
        """
        Parse a message looking for references, emoticons and links.

        :param message: A string
        :return: A JSON pretty printed string
        """
        if message is None or len(message) == 0:
            return '{}'

        details = self.parse_to_dict(message)
        return self.dict_to_json(details)

    def parse_to_dict(self, message):
        """
        Parse the given message for interesting details.

        :param message: A non-empty string
        :return: A dictionary of parsed information
        """
        d = dict()

        mentions = self._parse_mentions(message)
        if len(mentions):
            d[HipChatParser.DETAIL_MENTIONS] = mentions

        emoticons = self._parse_emoticons(message)
        if len(emoticons):
            d[HipChatParser.DETAIL_EMOTICONS] = emoticons

        links = self._parse_links(message)
        if len(links):
            d[HipChatParser.DETAIL_LINKS] = links

        return d

    def dict_to_json(self, d):
        """
        Convert the given dictionary to a pretty JSON string
        
        :param d: 
        :return:
        """
        s = json.dumps(d, sort_keys=True, indent=2)
        return s

    def _parse_mentions(self, message):
        """
        Parse the given message and return a list of users referenced in it

        :param message:
        :return: A possibly empty list of users
        """
        matches = [x[1:] for x in self._re_mentions.findall(message)]
        return matches

    def _parse_emoticons(self, message):
        """
        Parse the given message and return a list of emoticons listed in it

        :param message:
        :return: A possibly empty list of emoticons
        """
        matches = [x[1:-1] for x in self._re_emoticon.findall(message)]
        return matches

    def _parse_links(self, message):
        """
        Parse the given message and return a list of links mentioned in it.
        Each link is returned as a dictionary containing the url and title
        of the page indicated by the url

        :param message:
        :return: A possibly empty list of links
        """
        urls = self._re_url.findall(message)
        dicts = [{HipChatParser.DETAIL_URL: x, HipChatParser.DETAIL_TITLE: self.fetch_title(x)} for x in urls]
        return dicts

    def fetch_title(self, url):
        """
        Fetch the title of the page at the given url.
        If the given URL can't be fetched, or doesn't contain a <title> tag, then the URL itself will be returned

        :param url: A non-empty string in the format of a URL
        :return: The title of the given url's page
        """
        html = self._url_fetcher.get(url)
        match = self._re_title.search(html)
        if match:
            title = self._html_parser.unescape(match.groups(1)[0])
            return title
        else:
            return url


class UrlFetcher:
    """
    This class is a facade for fetching the first chunk of the contents of a URL.

    It allows us to play with different implementations (e.g. urllib2 vs Requests),
    as well as mock out the actual GET during unit tests
    """

    # At most this much of the url will be fetched, when looking for the title
    CHUNK_SIZE = 16 * 1024

    # NOTE: We could use the @lru_cache decorator on this method, after looking
    # to see if there are enough hits to be worth the costs

    def get(self, url):
        """
        Fetch the first chunk of the contents of the given URL.

        If the given url cannot be fetched within a sensible amount of time,
        return an empty string.
        """
        try:
            response = urllib2.urlopen(url)
            html = response.read(self.CHUNK_SIZE)
            return html
        except urllib2.URLError:
            # THINK - is it worth logging the exception? Probably not, since the url comes from user input
            return ""


class NullUrlFetcher:
    """
    Instances of this url fetcher simply return an empty string.
    """

    def get(self, url):
        return ''

def main():
    parser = HipChatParser()
    strings = [
        'String with any matching features but that is somewhat long)',
        'Good morning! (megusta) (coffee)',
        'Good morning! (thisIsTooLongToBeAnEmoticon)',
        'Olympics are starting soon; http://www.nbcolympics.com',
        '@bob @john (success) such a cool feature; https://twitter.com/jdorfman/status/430511497475670016'
    ]

    for x in strings:
        start = time.clock()
        result = parser.parse(x)
        duration = time.clock() - start
        print '{0:f} secs => {1}'.format(duration, result)

if __name__ == '__main__':
    main()
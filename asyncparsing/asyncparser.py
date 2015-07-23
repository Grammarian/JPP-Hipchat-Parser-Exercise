# -*- coding: utf-8 -*-

import logging
import Queue
import time
import threading
from hipchatparser import HipChatParser, NullUrlFetcher


class ParserWorkerThread(threading.Thread):
    """
    Instances of this class examine messages and fill in the title for any urls in the message
    """

    def __init__(self, thread_id, in_q, out_q, timeout=1):
        threading.Thread.__init__(self)
        self.daemon = True
        self.name = "Worker %d" % thread_id
        self._logger = logging.getLogger(self.name)
        self._in_q = in_q
        self._out_q = out_q
        self._timeout = timeout
        self._stopped = threading.Event()

        # Use a parser to do this lookup
        self._parser = HipChatParser()

    def run(self):
        self._logger.debug('Worker starting')
        while not self._stopped.is_set():
            try:
                item = self._in_q.get(True, self._timeout)
                self._worker_process(item)
                self._in_q.task_done()
            except Queue.Empty:
                # After sufficient time with no items being on the queue, we should probably reclaim this thread
                pass
        self._logger.debug('Worker stopping')

    def join(self, timeout=None):
        """
        Stop all processing on this thread
        """
        self._stopped.set()
        super(ParserWorkerThread, self).join(timeout)

    def _worker_process(self, msg):
        """
        Do the actual work of looking up titles of urls in the given message.
        If the message changes as a result of those lookups, dispatch an updated version of the message.
        """
        self._logger.debug('Processing: %s', msg)

        original_json = msg.details_as_json
        self._lookup_costly_details(msg)
        msg.details_as_json = self._parser.dict_to_json(msg.details)

        # Only dispatch an update if the details have changed
        if original_json != msg.details_as_json:
            self._out_q.put(msg)

    def _lookup_costly_details(self, msg):
        """
        Fill in whatever details we can about the message.
        """
        for d in msg.details[HipChatParser.DETAIL_LINKS]:
            d[HipChatParser.DETAIL_TITLE] = self._parser.fetch_title(d[HipChatParser.DETAIL_URL])


class AsyncParser:
    """
    Create a message parser which decodes details about the provided messages and dispatches
    the resulting augmented messages to an output queue.
    """

    _logger = logging.getLogger('AsyncParser')

    def __init__(self, number_workers=5):
        self._worker_q = Queue.Queue()
        self.out_q = Queue.Queue()
        self._number_workers = number_workers
        self._threads = []

        # Make a "fast" parser, by simply install a url fetcher that return an empty string.
        # (sometimes you just have to love the power of dependency injection :)
        self._fastParser = HipChatParser(NullUrlFetcher())

    def start(self):
        """
        Start pulling messages from the queue and dispatching them to the out queue
        """
        self._logger.debug('Starting...')
        # In a real app, we would manage these threads more intelligently
        self._threads = [self._create_worker(i) for i in range(self._number_workers)]
        self._logger.info('Started')

    def stop(self):
        """
        Shutdown this processor in an orderly fashion
        """
        self._logger.debug('Stopping...')
        for t in self._threads:
            t.join()
        self._logger.info('Stopped')

    def parse(self, msg):
        """
        Parses the given message and send the result to the output queue
        """
        self._logger.debug('Parsing: %s', msg)

        # Quickly decode the details that we can do without delay
        msg.details = self._fastParser.parse_to_dict(msg.text)
        msg.details_as_json = self._fastParser.dict_to_json(msg.details)

        # Pumps out the message. "slow" details are not yet filled in
        self.out_q.put(msg)

        # If the message had links, send it to the workers, which will
        # produced an updated message once the details are filled in
        if HipChatParser.DETAIL_LINKS in msg.details:
            self._worker_q.put(msg)

    def _create_worker(self, worker_id):
        """
        Create and start a worker that will collect more costly message details
        """
        w = ParserWorkerThread(worker_id, self._worker_q, self.out_q)
        w.start()
        return w


def main():

    class Message:
        """
        Simple DTO-style object representing a message in a chat system
        """

        def __init__(self, message_id, conversation_id, user_id, text):
            self.message_id = message_id
            self.conversation_id = conversation_id
            self.user_id = user_id
            self.text = text
            self.details = None

        def __str__(self):
            return "'%s' (user: %s, cid: %s, id: %s)" % (self.text, self.user_id, self.conversation_id, self.message_id)

    class Consumer(threading.Thread):
        """
        Simple consumer of a queue
        """

        _logger = logging.getLogger('Consumer')

        def __init__(self, q):
            threading.Thread.__init__(self)
            self._q = q
            self.daemon = True
            self._stopped = threading.Event()

        def run(self):
            self._logger.debug('Starting...')

            while not self._stopped.is_set():
                try:
                    msg = self._q.get(True, 1)
                    self._logger.info('%s', msg)
                    self._logger.info('JSON: %s', msg.details_as_json)
                    self._q.task_done()
                except Queue.Empty:
                    pass

            self._logger.debug('Stopped')

        def join(self, timeout=None):
            """
            Stop all processing on this thread
            """
            self._stopped.set()
            super(Consumer, self).join(timeout)

    init_logging()

    messages = [
        Message('guid1', 'c1', 'larry', 'morning @moe, morning @curly'),
        Message('guid2', 'c1', 'moe', 'morning @larry'),
        Message('guid3', 'c1', 'curly', 'morning @larry (sunrise)'),
        Message('guid4', 'c1', 'larry', 'i saw something fascinating last night'),
        Message('guid5', 'c1', 'larry', '@abbott @costelloa (thumbsup) https://www.youtube.com/watch?v=kTcRRaXV-fg'),
        Message('guid6', 'c1', 'larry', 'you can read all about the history here https://en.wikipedia.org/wiki/Who%27s_on_First%3F'),
        Message('guid7', 'c1', 'larry', "don't you think that's just so funny? (rotfl)"),
        Message('guid8', 'c1', 'moe', 'what did you see?'),
        Message('guid8', 'c1', 'curly', 'what was fascinating?')
    ]

    # Create a parser and hook its output to a consumer that will simply print the messages
    parser = AsyncParser()
    consumer = Consumer(parser.out_q)
    consumer.start()

    parser.start()
    for x in messages:
        parser.parse(x)
    parser.stop()
    consumer.join()


def init_logging():
    FORMAT = '%(asctime)s | %(name)s | %(levelname)s | %(thread)d | %(message)s'
    logging.basicConfig(format=FORMAT, level=logging.INFO)

if __name__ == '__main__':
    main()

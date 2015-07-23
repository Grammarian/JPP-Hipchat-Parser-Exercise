===============================
HipChat Message Parser
===============================

Implementation Discussion
-------------------------

The project, "hipchatparser", is the code I would submit for a coding assignment. It is simple,
clean, easy to understand, shows usage of python libraries, has unit tests and mockable interfaces.

It almost certainly couldn't be used in production in its current form. It does as was specified,
but as soon as it was used as part of a message pipeline, it's limitations would be obvious.

"asyncparser" is closer to something that might be used in production. Please read the following
discussion before reviewing the code for "asyncparser". I think doing so will make it clearer what
issues "asyncparser" is try to address (since they are well beyond what was originally spec'd).

The problem
-----------

The major problem with "hipchatparser" is the slowness of fetching a URL's title.
In it's current state, the parser delays all subsequent messages until the URL has been fetched and parsed.

This delay could be acceptable if:

* your architecture already separates the processing of each message into its own thread or process
* if the percentage of messages with links is small enough
* if each message has previous or subsequent processing that takes significantly more processing time,
  such that the delay of fetching the title is insignificant

However, if none of these conditions is true, then fetching the title will slow down subsequent
messages by several seconds. This seems unacceptable for a premium level chat system.

To get around this problem, we will need some sort of async processing. To do any async processing,
we need more than one message to process. And to process more than one message, we need some more data
rather than just strings.

Data models
-----------

[OK. Now I'm branching out beyond the spec, but this is exactly what I would be doing if I was part
of the HipChat team. I'm going to spread beyond simple message parsing and
into data models, architecture, and user experience :)]

Data model first. In a chat application, you would need at least these entities: Conversation,
User, Message. Basic relationships would be that a Conversation can have multiple participants (Users),
and that a Messages is part of a conversation and is sourced from a particular User.

So basic Message might look like this::

    class Message:
        def __init__(self, messageId, conversationId, userId, text):
            self._messageId = messageId
            self._conversationId = conversationId
            self._userId = userId
            self._text = text

Message pipelines
-----------------

To allow async processing, we need more than one message, so I'm going to imagine some sort of message
processing pipeline. Each stage is linked via some sort of async queuing mechanism.

A simple pipeline might look like:

    [reception] -> Q -> [parsing] -> Q -> [publishing] -> Q -> [persist]

[Aside: monitoring the size of the linking queues would provide wonderful real time insight into the
health of the system]

User experience
---------------

A naive async implementation might just delay messages with links, sending them on once all their extra
information has been gathered. But that would lead to a very odd user experience.
A message with a link could appear several seconds after a plain text message.

#1 - Joe: Hi Fred
#2 - Fred: hi joe
#3 - Joe: I found some thing interesting
#5 - Joe: what did you think of it?
#6 - Fred: about what?
#7 - Joe: the link i sent you
#8 - Fred: you didn't send me a link
[slow message arrives]
#4 - Joe: check out this link: [nice link with title]

I would imagine that a strong UX requirement would be that all messages
from a particular participant in a conversation must be displayed in the order they were sent.

Solution 1 - Update messages
----------------------------

If your architecture can handle messages being updated, then the slow title processing would be
fairly easy to handle.

I would change the parser to a "fast" parser, doing only what could be
done quickly, while marking those messages which required further slow processing. Those slow messages
would be given placeholders for url titles (or any other information that would be costly to calculate)
and dispatched in-order with the other, less costly messages.

The messages with placeholders would be placed into a queue. From there, worker threads would pick them up,
fetch the missing details, and then dispatch the filled in messages. That is,
an updated version of the slow message would be dispatched, with the placeholders replaced by real values.

So the user experience would be:

#1 - Joe: Hi Fred
#2 - Fred: hi joe
#3 - Joe: I found some thing interesting
#4 - Joe: check out this link: [raw http link]
#5 - Joe: what did you think of it?

[several second later, update to msg #4 arrives. clients now draw]
#4 - Joe: check out this link: [nice link with title]

One nice advantage of this is that wrong or dead URLs don't slow down processing at all. For such
dead links, there is no further information that we can add, so sending out the message with
placeholders turns out to be the best we could manage, and we've already sent it, so the whole
conversation was not slowed at all.

Solution 2 - Delayed user messages
----------------------------------

If messages cannot be updated, then the processing would be similar to the above: make a fast parser,
quickly dispatch fast messages, divert messages that require slow processing. However, once a message
from a user is diverted, all subsequent messages from that user in that conversation would also
have to be diverted to the *same* processing queue.

So the user experience would be:

#1 - Joe: Hi Fred
#2 - Fred: hi joe
#3 - Joe: I found some thing interesting
[delay for a few second]
#4 - Joe: check out this link: [nice link with title]
#5 - Joe: what did you think of it?

This is still at the mercy of links that take a long time to retrieve. A very slow or dead site
could take many seconds to return a response, and all of a users messages to a conversation would
be delayed until some response or timeout occurred.

Decision
--------

asyncparser is an implementation of Solution #1 -- updating messages.



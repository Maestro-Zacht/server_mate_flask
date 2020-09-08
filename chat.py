import os
import logging
import redis
import gevent
from flask import Flask
from flask_sockets import Sockets

REDIS_URL = os.environ['REDIS_URL']

app = Flask(__name__)
app.debug = 'DEBUG' in os.environ

sockets = Sockets(app)
redis = redis.from_url(REDIS_URL)


class ChatBackend:
    """Interface for registering and updating WebSocket clients."""

    def __init__(self):
        self.clients = {"albi": None, "bot": None}

        self.pubsub_to_albi = redis.pubsub()
        self.pubsub_to_albi.subscribe('albi')

        self.pubsub_to_bot = redis.pubsub()
        self.pubsub_to_bot.subscribe('bot')

    def __iter_data(self, pubsub):
        for message in pubsub.listen():
            data = message.get('data')
            if message['type'] == 'message':
                yield data

    def send(self, client, data):
        """Send given data to the registered client.
        Automatically discards invalid connections."""
        try:
            self.clients[client].send(data)
        except Exception:
            self.clients[client] = None
            print(f'connessione con {client} persa')

    def run_albi(self):
        """Listens for new messages in Redis, and sends them to clients."""
        for data in self.__iter_data(self.pubsub_to_albi):
            gevent.spawn(self.send, 'albi', data)

    def run_bot(self):
        for data in self.__iter_data(self.pubsub_to_bot):
            gevent.spawn(self.send, 'bot', data)

    def start(self):
        """Maintains Redis subscription in the background."""
        gevent.spawn(self.run_albi)
        gevent.spawn(self.run_bot)


chat = ChatBackend()
chat.start()


@sockets.route('/albi_riceve')
def albi_riceve(socket):
    chat.clients['albi'] = socket

    while not socket.closed:
        gevent.sleep(0.1)


@sockets.route('/bot_riceve')
def bot_riceve(socket):
    chat.clients['bot'] = socket

    while not socket.closed:
        gevent.sleep(0.1)


@sockets.route('/bot_manda')
def bot_manda(socket):
    while not socket.closed:
        # Sleep to prevent *constant* context-switches.
        gevent.sleep(0.1)
        message = socket.receive()

        if message:
            redis.publish('albi', message)


@sockets.route('/albi_manda')
def bot_manda(socket):
    while not socket.closed:
        # Sleep to prevent *constant* context-switches.
        gevent.sleep(0.1)
        message = socket.receive()

        if message:
            redis.publish('bot', message)

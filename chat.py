import logging
import os

import gevent
from flask import Flask
from flask_sockets import Sockets

app = Flask(__name__)
app.debug = 'DEBUG' in os.environ

sockets = Sockets(app)


class ChatBackend:
    """Interface for registering and updating WebSocket clients."""

    def __init__(self):
        self.clients = {"albi": [], "bot": []}

        self.queue_to_albi = gevent.queue.Queue()

        self.queue_to_bot = gevent.queue.Queue()

    def __iter_data(self, queue):
        for message in queue:
            yield message

    def send(self, target, client, data):
        """Send given data to the registered client.
        Automatically discards invalid connections."""
        try:
            client.send(data)
        except Exception:
            self.clients[target].remove(client)

    def run_albi(self):
        """Listens for new messages in Redis, and sends them to clients."""
        for data in self.__iter_data(self.queue_to_albi):
            for cl in self.clients['albi']:
                gevent.spawn(self.send, 'albi', cl, data)

    def run_bot(self):
        for data in self.__iter_data(self.queue_to_bot):
            for cl in self.clients['bot']:
                gevent.spawn(self.send, 'bot', data)

    def start(self):
        """Maintains Redis subscription in the background."""
        gevent.spawn(self.run_albi)
        gevent.spawn(self.run_bot)


chat = ChatBackend()
chat.start()


@sockets.route('/albi_riceve')
def albi_riceve(socket):
    socket.send("sei connesso alla ricezione albi")

    chat.clients['albi'].append(socket)

    while not socket.closed:
        gevent.sleep(0.1)


@sockets.route('/bot_riceve')
def bot_riceve(socket):
    socket.send("sei connesso alla ricezione bot")

    chat.clients['bot'].append(socket)

    while not socket.closed:
        gevent.sleep(0.1)


@sockets.route('/bot_manda')
def bot_manda(socket):
    socket.send("sei connesso al manda bot")

    while not socket.closed:
        # Sleep to prevent *constant* context-switches.
        gevent.sleep(0.1)
        message = socket.receive()

        if message:
            chat.queue_to_albi.put(message)


@sockets.route('/albi_manda')
def bot_manda(socket):
    socket.send("sei connesso al manda albi")

    while not socket.closed:
        # Sleep to prevent *constant* context-switches.
        gevent.sleep(0.1)
        message = socket.receive()

        if message:
            chat.queue_to_bot.put(message)

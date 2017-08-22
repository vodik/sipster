import asyncio

import aiosip

from .app import Application
from .dialog import Dialog, Response, Request


class UserAgent:
    def __init__(self, *, to_uri=None, from_uri=None, contact_uri=None,
                 password=None, remote_addr=None, local_addr=None):
        self.app = Application(self)
        self.dialog = None
        self.queue = asyncio.Queue()
        self.cseq = 0
        self.call_id = None
        self.method_routes = {}
        self.require_ack = False

        self.to_uri = to_uri
        self.from_uri = from_uri
        self.contact_uri = contact_uri
        self.password = password
        self.remote_addr = remote_addr
        self.local_addr = local_addr

    def add_route(self, method, callback):
        self.method_routes[method] = callback

    @asyncio.coroutine
    def recv(self, msg_type):
        while True:
            msg = yield from asyncio.wait_for(self.queue.get(), timeout=60)
            if not self.call_id:
                self.call_id = msg.headers['Call-ID']

            if isinstance(msg, msg_type):
                break

        return msg

    @asyncio.coroutine
    def recv_request(self, method, ignore=[]):
        while True:
            msg = yield from self.recv(aiosip.Request)
            if self.call_id and msg.headers['Call-ID'] != self.call_id:
                continue

            if msg.method not in ignore:
                break

        if not self.cseq:
            cseq, _, _ = msg.headers['CSeq'].partition(' ')
            self.cseq = int(cseq)

        if msg.method != method:
            raise RuntimeError('Unexpected message, expected {}, '
                               'found {}'.format(method, msg.method))
        request = Request(self, msg)
        print("Received:", request.firstline)
        return request

    @asyncio.coroutine
    def recv_response(self, status, ignore=[]):
        status_code, status_message = status.split(' ', 1)
        status_code = int(status_code)

        while True:
            msg = yield from self.recv(aiosip.Response)
            if not self.call_id:
                self.call_id = msg.headers['Call-ID']
            elif self.call_id and msg.headers['Call-ID'] != self.call_id:
                continue

            if msg.status_code not in ignore:
                break

        response = Response(self, msg)
        if msg.status_code != status_code:
            if self.require_ack:
                response.ack()

            raise RuntimeError('Unexpected message, expected {}, '
                               'found {} {}'.format(status_code,
                                                    msg.status_code,
                                                    msg.status_message))
        response = Response(self, msg)
        print("Received:", response.firstline)
        return response

    def send_request(self, method: str, *, headers=None, **kwargs):
        if not headers:
            headers = {}

        # Make sure we track state if an ack is required or not for
        # exception recovery.
        if method == 'INVITE':
            self.require_ack = True
        elif method == 'ACK':
            self.require_ack = False

        if not 'CSeq' in headers:
            self.cseq += 1
            headers['CSeq'] = '{} {}'.format(self.cseq, method)
        else:
            cseq, _, _ = headers['CSeq'].partition(' ')
            self.cseq = int(cseq)

        print("Sent:", method)
        return self.dialog.send_message(method, headers=headers.copy(), **kwargs)

    def send_response(self, status: str, *, headers=None, **kwargs):
        status_code, status_message = status.split(' ', 1)
        print("Sent:", status)
        self.dialog.send_reply(int(status_code), status_message,
                               headers=headers.copy(), **kwargs)

    def close(self):
        if self.dialog:
            self.dialog.close()
            for transport in self.app._transports.values():
                transport.close()
            self.dialog = None


class Client(UserAgent):
    @asyncio.coroutine
    def start(self):
        if self.dialog:
            return

        self.dialog = yield from self.app.start_dialog(
            remote_addr=self.remote_addr,
            to_uri=self.to_uri,
            from_uri=self.from_uri,
            contact_uri=self.contact_uri,
            password=self.password,
            dialog=lambda *a, **kw: Dialog(self, *a, **kw)
        )
        self.app.dialog_ready.set_result(self.dialog)

    @asyncio.coroutine
    def run(self, scenario):
        yield from self.start()
        result = yield from scenario(self)
        return result


class Server(UserAgent):
    @asyncio.coroutine
    def listen(self):
        local_addr = self.local_addr
        if local_addr is None:
            contact = aiosip.Contact.from_header(self.contact_uri)
            local_addr = (contact['uri']['host'],
                          contact['uri']['port'])

        yield from self.app.create_connection(aiosip.UDP, local_addr, None,
                                              mode='server')

    @asyncio.coroutine
    def serve(self, scenario):
        yield from self.listen()
        yield from asyncio.wait_for(self.app.dialog_ready, timeout=60)
        result = yield from scenario(self)
        return result

import asyncio
from typing import Union, List

import aiosip
import multidict


class Dialog(aiosip.Dialog):
    def __init__(self, agent, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agent = agent

    def receive_message(self, msg):
        self.agent.queue.put_nowait(msg)


class Request:
    def __init__(self, agent, data):
        self.agent = agent
        self.data = data

    def __getattr__(self, key):
        return getattr(self.data, key)

    def respond(self, *args, **kwargs):
        headers = kwargs.pop('headers', {})
        headers['CSeq'] = self.data.headers['CSeq']
        return self.agent.send_response(*args, **kwargs, headers=headers,
                                        to_details=self.data.to_details,
                                        from_details=self.data.from_details)

    def __str__(self):
        return str(self.data)

    def __repr__(self):
        message = str(self)
        first_line = message[:message.find('\r\n')]
        return f'{self.__class__.__name__}<{first_line}>'


class Response:
    def __init__(self, agent, data):
        self.agent = agent
        self.data = data

    def __getattr__(self, key):
        return getattr(self.data, key)

    def ack(self, *args, **kwargs):
        return self.respond(*args, **kwargs)

    def respond(self, *args, **kwargs):
        headers = kwargs.pop('headers', {})
        cseq, _, _ = self.data.headers['CSeq'].partition(' ')

        headers['CSeq'] = f'{cseq} ACK'
        return self.agent.send_request('ACK', *args, **kwargs, headers=headers,
                                       to_details=self.data.to_details,
                                       from_details=self.data.from_details)

    def __str__(self):
        return str(self.data)

    def __repr__(self):
        message = str(self)
        first_line = message[:message.find('\r\n')]
        return f'{self.__class__.__name__}<{first_line}>'


class Application(aiosip.Application):
    def __init__(self, agent):
        super().__init__()
        self.agent = agent
        self.dialog_ready = asyncio.Future()

    async def handle_incoming(self, protocol, msg, addr):
        if self.dialog_ready.done():
            return

        if self.agent.local_addr:
            local_addr = self.agent.local_addr
        else:
            local_addr = (msg.to_details['uri']['host'],
                          msg.to_details['uri']['port'])

        remote_addr = (msg.contact_details['uri']['host'],
                       msg.contact_details['uri']['port'])

        proto = await self.create_connection(protocol, local_addr, remote_addr)
        dlg = Dialog(self.agent,
                     app=self,
                     from_uri=msg.headers['From'],
                     to_uri=msg.headers['To'],
                     contact_uri=self.agent.contact_uri,
                     call_id=msg.headers['Call-ID'],
                     protocol=proto,
                     local_addr=local_addr,
                     remote_addr=remote_addr,
                     password=None,
                     loop=self.loop)

        self._dialogs[msg.headers['Call-ID']] = dlg
        dlg.receive_message(msg)
        self.dialog_ready.set_result(dlg)

    def dispatch(self, protocol, msg, addr):
        key = msg.headers['Call-ID']
        if key in self._dialogs:
            self._dialogs[key].receive_message(msg)
        else:
            self.loop.call_soon(asyncio.ensure_future,
                                self.handle_incoming(protocol, msg, addr))


class UserAgent:
    def __init__(self, *, to_uri=None, from_uri=None, contact_uri=None,
                 password=None, remote_addr=None, local_addr=None):
        self.app = Application(self)
        self.dialog = None
        self.queue = asyncio.Queue()
        self.cseq = 0
        self.message_callback = None
        self.method_routes = multidict.CIMultiDict()

        self.to_uri = to_uri
        self.from_uri = from_uri
        self.contact_uri = contact_uri
        self.password = password
        self.remote_addr = remote_addr
        self.local_addr = local_addr

    async def get_dialog(self):
        if not self.dialog:
            self.dialog = await asyncio.wait_for(self._get_dialog(), timeout=30)
        return self.dialog

    def add_receive_callback(self, callback):
        self.message_callback = callback

    def add_route(self, method, callback):
        self.method_routes[method] = callback

    async def recv(self, msg_type):
        dialog = await self.get_dialog()
        while True:
            msg = await asyncio.wait_for(self.queue.get(), timeout=30)

            wrapped_msg = self._wrap_msg(msg)
            if self.message_callback:
                response = self.message_callback(wrapped_msg)
                if response:
                    await wrapped_msg.respond(response)
                    continue

            route = self.method_routes.get(msg.method)
            if route:
                response = route(wrapped_msg)
                if response:
                    await wrapped_msg.respond(response)
                    continue

            if isinstance(msg, msg_type):
                break
        return msg

    async def recv_request(self, method, ignore=[]):
        while True:
            msg = await self.recv(aiosip.Request)
            if msg.method not in ignore:
                break

        if not self.cseq:
            cseq, _, _ = msg.headers['CSeq'].partition(' ')
            self.cseq = int(cseq)

        if msg.method != method:
            raise RuntimeError(f'Unexpected message, expected {method}, '
                               f'found {msg.method}')
        print("Recieved:", str(msg).splitlines()[0])
        return Request(self, msg)

    async def recv_response(self, status, ignore=[]):
        status_code, status_message = status.split(' ', 1)
        status_code = int(status_code)

        while True:
            msg = await self.recv(aiosip.Response)
            if msg.status_code not in ignore:
                break

        if msg.status_code != status_code:
            raise RuntimeError(f'Unexpected message, expected {status_code}, '
                               f'found {msg.status_code}')
        print("Recieved:", str(msg).splitlines()[0])
        return Response(self, msg)

    async def send_request(self, method: str, *, headers=None, **kwargs):
        dialog = await self.get_dialog()
        if not headers:
            headers = {}

        if not 'CSeq' in headers:
            self.cseq += 1
            headers['CSeq'] = f'{self.cseq} {method}'
        else:
            cseq, _, _ = headers['CSeq'].partition(' ')
            self.cseq = int(cseq)

        print("Sending:", method)
        dialog.send_message(method, headers=headers.copy(), **kwargs)

    async def send_response(self, status: str, *, headers=None, **kwargs):
        dialog = await self.get_dialog()
        status_code, status_message = status.split(' ', 1)

        print("Sending:", status)
        dialog.send_reply(int(status_code), status_message, headers=headers.copy(), **kwargs)

    def close(self):
        if self.dialog:
            self.dialog.close()
            for transport in  self.app._transports.values():
                transport.close()
            self.dialog = None

    def _wrap_msg(self, msg):
        if isinstance(msg, aiosip.Request):
            return Request(self, msg)
        else:
            return Response(self, msg)


class Client(UserAgent):
    async def _get_dialog(self):
        return await self.app.start_dialog(
            remote_addr=self.remote_addr,
            to_uri=self.to_uri,
            from_uri=self.from_uri,
            contact_uri=self.contact_uri,
            password=self.password,
            dialog=lambda *a, **kw: Dialog(self, *a, **kw)
        )


class Server(UserAgent):
    def _get_dialog(self):
        return self.app.dialog_ready

    async def listen(self):
        local_addr = self.local_addr
        if local_addr is None:
            contact = aiosip.Contact.from_header(self.contact_uri)
            local_addr = (contact['uri']['host'],
                          contact['uri']['port'])

        await self.app.create_connection(aiosip.UDP, local_addr, None,
                                         mode='server')

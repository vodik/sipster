import asyncio
from typing import Union, List

import aiosip


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

    async def respond(self, *args, **kwargs):
        headers = kwargs.pop('headers', {})
        headers['CSeq'] = self.data.headers['CSeq']
        return await self.agent.send_response(*args, **kwargs, headers=headers)

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
            self.loop.call_soon(asyncio.async,
                                self.handle_incoming(protocol, msg, addr))


class UserAgent:
    def __init__(self, *, to_uri=None, from_uri=None, contact_uri=None,
                 password=None, remote_addr=None, local_addr=None):
        self.app = Application(self)
        self.dialog = None
        self.queue = asyncio.Queue()

        self.to_uri = to_uri
        self.from_uri = from_uri
        self.contact_uri = contact_uri
        self.password = password
        self.remote_addr = remote_addr
        self.local_addr = local_addr

    async def get_dialog(self):
        if not self.dialog:
            self.dialog = await asyncio.wait_for(self._get_dialog(), timeout=5)
        return self.dialog

    async def recv(self, msg_type):
        dialog = await self.get_dialog()
        while True:
            msg = await asyncio.wait_for(self.queue.get(), timeout=5)
            if isinstance(msg, msg_type):
                break
        return msg

    async def recv_request(self, method, ignore=[]):
        while True:
            msg = await self.recv(aiosip.Request)
            if msg.method not in ignore:
                break

        if msg.method != method:
            raise RuntimeError(f'Unexpected message, expected {method}, '
                               f'found {msg.method}')
        print("Recieved:", str(msg).splitlines()[0])
        return Request(self, msg)

    async def recv_response(self, status_code, ignore=[]):
        while True:
            msg = await self.recv(aiosip.Response)
            if msg.status_code not in ignore:
                break

        if msg.status_code != status_code:
            raise RuntimeError(f'Unexpected message, expected {status_code}, '
                               f'found {msg.status_code}')
        print("Recieved:", str(msg).splitlines()[0])
        return msg

    async def send_request(self, method: str, *, headers=None):
        dialog = await self.get_dialog()
        dialog.send_message(method, headers=headers)

    async def send_response(self, status: str, *, headers=None):
        dialog = await self.get_dialog()
        status_code, status_message = status.split()
        dialog.send_reply(int(status_code), status_message, headers=headers)


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

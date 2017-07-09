import asyncio
from typing import Union, List

import aiosip


class Dialog(aiosip.Dialog):
    def __init__(self, agent, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agent = agent

    def receive_message(self, msg):
        self.agent.queue.put_nowait(msg)


class Application(aiosip.Application):
    def __init__(self, agent):
        super().__init__()
        self.agent = agent
        self.dialog_ready = asyncio.Future()

    async def handle_incoming(self, protocol, msg, addr, route):
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
            self.dialog = await self._get_dialog()
        return self.dialog

    async def recv(self, method: Union[str, int],
                   ignore: List[int]=[]):
        dialog = await self.get_dialog()

        while True:
            msg = await self.queue.get()
            if not ignore:
                break
            elif msg.status_code not in ignore:
                break

        if isinstance(method, int):
            if msg.status_code != method:
                raise RuntimeError(f'Unexpected message, expected {method}, '
                                   f'found {msg.status_code}')
        else:
            if msg.method != method:
                raise RuntimeError(f'Unexpected message, expected {method}, '
                                   f'found {msg.method}')

        return msg

    async def send(self, method: Union[str, int], *, headers=None,
                   payload: str=None) -> None:
        dialog = await self.get_dialog()
        dialog.send_message(method, headers=headers)


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

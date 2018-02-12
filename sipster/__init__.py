import asyncio
import aiosip


class UserAgent:
    def __init__(self, server, peer, to_details, from_details, contact_details):
        self._server = server
        self._peer = peer
        self._dialog = None
        self.to_details = to_details
        self.from_details = from_details
        self.contact_details = contact_details

    async def _default_handler(self, dialog, request):
        print(request.payload)
        await dialog.reply(request, status_code=200)

    async def _get_dialog(self):
        if not self._dialog:
            self._dialog = self._peer.create_dialog(
                from_details=self.from_details,
                to_details=self.to_details,
                contact_details=self.contact_details,
                router={'*', self._default_handler}
            )
        return self._dialog

    # def add_receive_callback(self, callback):
    #     ...

    # def add_route(self, method, callback):
    #     ...

    def recv_request(self, method, ignore=[]):
        return asyncio.Future()

    def recv_response(self, status, ignore=[]):
        return asyncio.Future()

    async def send_request(self, method: str, *, headers=None, **kwargs):
        dialog = await self._get_dialog()
        await dialog.request(method, headers=headers, **kwargs)

    async def send_response(self, status: str, *, headers=None, **kwargs):
        if not self._dialog:
            raise RuntimeError("No dialog has been established yet")

        raise NotImplementedError("can't")

    def close(self):
        ...


class Application():
    def __init__(self):
        self._app = aiosip.Application()

    async def add_ua(self, *, to_uri, from_uri, contact_uri,
                     protocol=aiosip.UDP):
        from_details = aiosip.Contact.from_header(from_uri)
        to_details = aiosip.Contact.from_header(to_uri)
        contact_details = aiosip.Contact.from_header(contact_uri)

        local_addr = contact_details['uri']['host'], contact_details['uri']['port']
        remote_addr = to_details['uri']['host'], to_details['uri']['port']

        server = await self._app.run(local_addr=local_addr, protocol=protocol)
        peer = await self._app.connect(remote_addr=remote_addr, protocol=protocol)
        return UserAgent(server, peer, to_details, from_details, contact_details)

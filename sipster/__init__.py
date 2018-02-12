import asyncio
import aiosip


class Request:
    def __init__(self, dialog, msg):
        self._dialog = dialog
        self._msg = msg

    async def respond(self, status_code):
        await self._dialog.reply(self._msg, status_code)


class UserAgent:
    def __init__(self, server, peer, to_details, from_details, contact_details):
        self._server = server
        self._peer = peer
        self._dialog = None
        self._queue = asyncio.Queue()
        self.to_details = to_details
        self.from_details = from_details
        self.contact_details = contact_details

    async def _default_handler(self, dialog, request):
        print("CAUGHT", request)
        assert dialog == self._dialog
        await self._queue.put(Request(dialog, request))

    async def _get_dialog(self):
        if not self._dialog:
            self._dialog = self._peer.create_dialog(
                from_details=self.from_details,
                to_details=self.to_details,
                contact_details=self.contact_details,
                router=aiosip.Router(default=self._default_handler)
            )
        return self._dialog

    def recv_request(self, method, ignore=[]):
        return self._queue.get()

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


class Application(aiosip.Application):
    def __init__(self):
        super().__init__()
        self._useragents = {}

    async def _dispatch(self, protocol, msg, addr):
        connector = self._connectors[type(protocol)]
        peer = await connector.get_peer(protocol, addr)
        key = msg.headers['Call-ID']
        dialog = peer._dialogs.get(key)
        if not dialog:
            useragent = self._useragents[protocol]
            dialog = await useragent._get_dialog()
        await dialog.receive_message(msg)

    async def add_ua(self, *, to_uri, from_uri, contact_uri,
                     protocol=aiosip.UDP):
        from_details = aiosip.Contact.from_header(from_uri)
        to_details = aiosip.Contact.from_header(to_uri)
        contact_details = aiosip.Contact.from_header(contact_uri)

        local_addr = contact_details['uri']['host'], contact_details['uri']['port']
        remote_addr = to_details['uri']['host'], to_details['uri']['port']

        server = await self.run(local_addr=local_addr, protocol=protocol)
        peer = await self.connect(remote_addr=remote_addr, protocol=protocol)

        agent = UserAgent(server, peer, to_details, from_details, contact_details)
        self._useragents[server] = agent
        return agent

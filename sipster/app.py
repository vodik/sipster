import asyncio

import aiosip


class Application(aiosip.Application):
    def __init__(self, agent):
        super().__init__()
        self.agent = agent
        self.dialog_ready = asyncio.Future()

    @asyncio.coroutine
    def handle_incoming(self, protocol, msg, addr):
        if self.dialog_ready.done():
            return

        if self.agent.local_addr:
            local_addr = self.agent.local_addr
        else:
            local_addr = (msg.to_details['uri']['host'],
                          msg.to_details['uri']['port'])

        remote_addr = addr
        # remote_addr = (msg.contact_details['uri']['host'],
        #                msg.contact_details['uri']['port'])

        print(local_addr, remote_addr)
        proto = yield from self.create_connection(protocol, local_addr,
                                                  remote_addr)
        yield from proto.ready

        dialog = Dialog(self.agent,
                        app=self,
                        # from_uri=msg.headers['From'],
                        # to_uri=msg.headers['To'],
                        to_uri=self.agent.to_uri,
                        from_uri=self.agent.from_uri,
                        contact_uri=self.agent.contact_uri,
                        call_id=msg.headers['Call-ID'],
                        protocol=proto,
                        local_addr=local_addr,
                        remote_addr=remote_addr,
                        password=None,
                        loop=self.loop)

        self.agent.dialog = dialog
        dialog.receive_message(msg)

        self._dialogs[msg.headers['Call-ID']] = dialog
        self.dialog_ready.set_result(dialog)

    def dispatch(self, protocol, msg, addr):
        if self.dialog_ready.done():
            self.agent.dialog.receive_message(msg)
        else:
            self.loop.call_soon(asyncio.ensure_future,
                                self.handle_incoming(protocol, msg, addr))

        # key = msg.headers['Call-ID']
        # if key in self._dialogs:
        #     self._dialogs[key].receive_message(msg)
        # else:
        #     self.loop.call_soon(asyncio.ensure_future,
        #                         self.handle_incoming(protocol, msg, addr))

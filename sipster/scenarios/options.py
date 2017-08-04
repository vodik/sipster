import asyncio

from sipster import Client, Server, Request


async def server(ua):
    invite = await ua.recv_request('INVITE')
    await invite.respond('100 Trying')
    await invite.respond('180 Ringing')
    await invite.respond('200 OK')
    await ua.recv_request('ACK')

    await ua.send_request('OPTIONS')
    await ua.recv_response('200 OK')

    await asyncio.sleep(1)

    await ua.send_request('BYE')
    await ua.recv_response('200 OK')


async def client(ua):
    await ua.send_request('INVITE')
    response = await ua.recv_response('200 OK', ignore=[100, 180, 183])
    await response.ack()

    bye = await ua.recv_request('BYE')
    await bye.respond('200 OK')


async def options():
    def on_options(msg):
        return '200 OK'

    uac = Client(to_uri=f'"sut" <sip:service@127.0.0.1:59361>',
                 from_uri=f'"sipp" <sip:sipp@127.0.0.1:47398>',
                 contact_uri=f'sip:service@127.0.0.1:47398')
    uac.add_route('OPTIONS', on_options)

    uas = Server(to_uri=f'"sipp" <sip:sipp@127.0.0.1:47398>',
                 from_uri=f'"sut" <sip:service@127.0.0.1:59361>',
                 contact_uri=f'sip:sipp@127.0.0.1:59361')

    await uas.listen()
    await asyncio.gather(client(uac), server(uas))


loop = asyncio.get_event_loop()
loop.run_until_complete(options())
loop.close()

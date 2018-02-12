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


async def options(args=[]):
    uac = Client(to_uri='"sut" <sip:service@127.0.0.1:59361>',
                 from_uri='"sipp" <sip:sipp@127.0.0.1:47398>',
                 contact_uri='sip:service@127.0.0.1:47398')

    uas = Server(to_uri='"sipp" <sip:sipp@127.0.0.1:47398>',
                 from_uri='"sut" <sip:service@127.0.0.1:59361>',
                 contact_uri='sip:sipp@127.0.0.1:59361')

    uac.add_route('OPTIONS', lambda msg: '200 OK')

    await uas.listen()
    return client(uac), server(uas)

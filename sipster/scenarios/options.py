import asyncio

from sipster import Client, Server, Request


@asyncio.coroutine
def server(ua):
    invite = yield from ua.recv_request('INVITE')
    yield from invite.respond('100 Trying')
    yield from invite.respond('180 Ringing')
    yield from invite.respond('200 OK')
    yield from ua.recv_request('ACK')

    yield from ua.send_request('OPTIONS')
    yield from ua.recv_response('200 OK')

    yield from asyncio.sleep(1)

    yield from ua.send_request('BYE')
    yield from ua.recv_response('200 OK')


@asyncio.coroutine
def client(ua):
    yield from ua.send_request('INVITE')
    response = yield from ua.recv_response('200 OK', ignore=[100, 180, 183])
    yield from response.ack()

    bye = yield from ua.recv_request('BYE')
    yield from bye.respond('200 OK')


@asyncio.coroutine
def options(args=[]):
    uac = Client(to_uri=f'"sut" <sip:service@127.0.0.1:59361>',
                 from_uri=f'"sipp" <sip:sipp@127.0.0.1:47398>',
                 contact_uri=f'sip:service@127.0.0.1:47398')

    uas = Server(to_uri=f'"sipp" <sip:sipp@127.0.0.1:47398>',
                 from_uri=f'"sut" <sip:service@127.0.0.1:59361>',
                 contact_uri=f'sip:sipp@127.0.0.1:59361')

    uac.add_route('OPTIONS', lambda msg: '200 OK')

    yield from uas.listen()
    return client(uac), server(uas)

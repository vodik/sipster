import asyncio

from sipster import Client, Server


@asyncio.coroutine
def server(ua):
    invite = yield from ua.recv_request('INVITE')
    invite.respond('100 Trying')
    invite.respond('180 Ringing')
    invite.respond('200 OK')
    yield from ua.recv_request('ACK')

    yield from asyncio.sleep(1)

    ua.send_request('BYE')
    yield from ua.recv_response('200 OK')


@asyncio.coroutine
def client(ua):
    ua.send_request('INVITE')
    response = yield from ua.recv_response('200 OK', ignore=[100, 180, 183])
    response.ack()

    bye = yield from ua.recv_request('BYE')
    bye.respond('200 OK')


@asyncio.coroutine
def fastanswer(args=[]):
    uac = Client(to_uri='"sut" <sip:service@127.0.0.1:59361>',
                 from_uri='"sipp" <sip:sipp@127.0.0.1:47398>',
                 contact_uri='sip:service@127.0.0.1:47398')

    uas = Server(to_uri='"sipp" <sip:sipp@127.0.0.1:47398>',
                 from_uri='"sut" <sip:service@127.0.0.1:59361>',
                 contact_uri='sip:sipp@127.0.0.1:59361')

    return (uas.serve(server), uac.run(client))

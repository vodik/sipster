import asyncio

from useragent import Client, Server


async def server(ua):
    response = await ua.recv_request('INVITE')

    await ua.send_response('200 OK')
    await ua.recv_request('ACK')

    response = await ua.recv_request('BYE')
    await ua.send_response('200 OK')


async def client(ua):
    await ua.send_request('INVITE')
    await ua.recv_response(200, ignore=[100, 180])
    await ua.send_request('ACK')

    await asyncio.sleep(1)

    await ua.send_request('BYE')
    await ua.recv_response(200)


async def fastanswer():
    uac = Client(to_uri=f'"sut" <sip:service@127.0.0.1:59361>',
                 from_uri=f'"sipp" <sip:sipp@127.0.0.1:47398>',
                 contact_uri=f'sip:service@127.0.0.1:47398')

    uas = Server(to_uri=f'"sipp" <sip:sipp@127.0.0.1:47398>',
                 from_uri=f'"sut" <sip:service@127.0.0.1:59361>',
                 contact_uri=f'sip:sipp@127.0.0.1:59361')

    await uas.listen()
    await asyncio.gather(client(uac), server(uas))


loop = asyncio.get_event_loop()
loop.run_until_complete(fastanswer())
loop.close()

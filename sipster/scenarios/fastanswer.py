import asyncio


async def server(ua):
    invite = await ua.recv('INVITE')
    await invite.respond(100)
    await invite.respond(180)
    await invite.respond(200)
    await invite.acked()

    await asyncio.sleep(1)

    bye = await ua.send('BYE')
    await bye.recv(200)


async def client(ua):
    invite = await ua.send('INVITE')
    await invite.recv(200, ignore=[100, 180, 183])
    await invite.ack()

    bye = await ua.recv('BYE')
    await bye.respond(200)


async def fastanswer(app, args=[]):
    uac = await app.add_ua(to_uri='"sut" <sip:service@127.0.0.1:59361>',
                           from_uri='"sipp" <sip:sipp@127.0.0.1:47398>',
                           contact_uri='sip:service@127.0.0.1:47398')

    uas = await app.add_ua(to_uri='"sipp" <sip:sipp@127.0.0.1:47398>',
                           from_uri='"sut" <sip:service@127.0.0.1:59361>',
                           contact_uri='sip:sipp@127.0.0.1:59361')

    return client(uac), server(uas)

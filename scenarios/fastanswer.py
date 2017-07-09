import asyncio
from useragent import Client, Server


async def server(user_agent):
    response = await user_agent.recv('INVITE')
    print('RECIEVED', response)

    # await user_agent.send(200, headers={}, payload='')
    # await user_agent.recv('ACK')

    # response = await user_agent.recv('BYE')
    # await user_agent.send(200)


async def client(user_agent):
    await user_agent.send('INVITE')
    # await user_agent.recv(200, ignore=[100, 180])
    # await user_agent.send('ACK')

    # await asyncio.sleep(5)

    # await user_agent.send('BYE')
    # await user_agent.recv(200)


async def fastanswer():
    uac = Client(to_uri=f'"sut" <sip:service@127.0.0.1:59361>',
                 from_uri=f'"sipp" <sip:sipp@127.0.0.1:47398>',
                 contact_uri=f'sip:service@127.0.0.1:47398')

    uas = Server(to_uri=f'"sipp" <sip:sipp@127.0.0.1:47398>',
                 from_uri=f'"sut" <sip:service@127.0.0.1:59361>',
                 contact_uri=f'sip:sipp@127.0.0.1:59361')

    # uac = Client(to_uri=f'"sut" <sip:service@10.200.0.2:59361>',
    #              from_uri=f'"sipp" <sip:sipp@10.200.0.2:47398>',
    #              contact_uri=f'sip:service@10.200.0.2:47398',
    #              remote_addr=('10.10.8.40', 5060))

    # uas = Server(to_uri=f'"sipp" <sip:sipp@10.200.0.2:47398>',
    #              from_uri=f'"sut" <sip:service@10.200.0.2:59361>',
    #              contact_uri=f'sip:sipp@10.200.0.2:59361')

    await uas.listen()
    await asyncio.gather(client(uac), server(uas))


loop = asyncio.get_event_loop()
loop.run_until_complete(fastanswer())
loop.close()

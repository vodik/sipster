import aiosip


class Dialog(aiosip.Dialog):
    def __init__(self, agent, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agent = agent

    def process_callback(self, msg):
        route = self.agent.method_routes.get(msg.method)
        if route:
            request = Request(self.agent, msg)
            response = route(request)
            if response:
                print('--------->', msg.from_details['uri']['user'])
                if msg.from_details['uri']['user'] == 'searcher':
                    contact = aiosip.Contact.from_header(self.agent.contact_uri)
                    contact['uri']['user'] = 'searcher'
                    request.respond(response, contact_details=contact)
                else:
                    request.respond(response)

                return True

        return False

    def receive_message(self, msg):
        if isinstance(msg, aiosip.Request) and self.process_callback(msg):
            return
        self.agent.queue.put_nowait(msg)


class Request:
    def __init__(self, agent, data):
        self.agent = agent
        self.data = data

    def __getattr__(self, key):
        return getattr(self.data, key)

    def respond(self, *args, **kwargs):
        headers = kwargs.pop('headers', {})
        headers['CSeq'] = self.data.headers['CSeq']
        headers['Call-ID'] = self.data.headers['Call-ID']
        headers['Via'] = self.data.headers['Via']
        return self.agent.send_response(*args, **kwargs, headers=headers,
                                        to_details=self.data.to_details,
                                        from_details=self.data.from_details)

    @property
    def firstline(self):
        return str(self.data).splitlines()[0]

    def __str__(self):
        return str(self.data)

    def __repr__(self):
        message = str(self)
        first_line = message[:message.find('\r\n')]
        return '{}<{}>'.format(self.__class__.__name__, first_line)


class Response:
    def __init__(self, agent, data):
        self.agent = agent
        self.data = data

    def __getattr__(self, key):
        return getattr(self.data, key)

    def ack(self, *args, **kwargs):
        return self._respond('ACK', *args, **kwargs)

    def cancel(self, *args, **kwargs):
        return self._respond('CANCEL', *args, **kwargs)

    def _respond(self, method, *args, **kwargs):
        headers = kwargs.pop('headers', {})
        cseq, _, _ = self.data.headers['CSeq'].partition(' ')

        headers['CSeq'] = '{} {}'.format(cseq, method)
        headers['Via'] = self.data.headers['Via']
        return self.agent.send_request(method, *args, **kwargs,
                                       headers=headers,
                                       to_details=self.data.to_details,
                                       from_details=self.data.from_details)

    @property
    def firstline(self):
        return str(self.data).splitlines()[0]

    def __str__(self):
        return str(self.data)

    def __repr__(self):
        message = str(self)
        first_line = message[:message.find('\r\n')]
        return '{}<{}>'.format(self.__class__.__name__, first_line)

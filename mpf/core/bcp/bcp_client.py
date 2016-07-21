import abc


class BaseBcpClient(metaclass=abc.ABCMeta):

    def __init__(self, machine, name, bcp):
        self.name = name
        self.machine = machine
        self.bcp = bcp

    def connect(self, config):
        raise NotImplementedError("implement")

    def accept_connection(self, receiver, sender):
        raise NotImplementedError("implement")

    def send(self, bcp_command, kwargs):
        raise NotImplementedError("implement")

    def stop(self):
        raise NotImplementedError("implement")
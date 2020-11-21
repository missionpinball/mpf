import logging
import asyncio
import grpc
from grpc.experimental import aio

from mpf.platforms.visual_pinball_engine import platform_pb2_grpc
from mpf.platforms.visual_pinball_engine import platform_pb2


class MpfHardwareService(platform_pb2_grpc.MpfHardwareServiceServicer):

    def Start(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def SendSwitchChanges(self, request_iterator, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def Quit(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

async def switch_generator():
    state = True
    while True:
        print("+")
        state = not state
        change = platform_pb2.SwitchChanges()
        change.switch_number = "0"
        change.switch_state = state
        yield change
        await asyncio.sleep(1)

async def connect():
    channel = aio.insecure_channel("localhost:50051")
    await channel.channel_ready()
    stub = platform_pb2_grpc.MpfHardwareServiceStub(channel)
    configuration = platform_pb2.MachineConfiguration(
            known_switches_with_initial_state={"0": True, "3": False, "6": False},
            known_lights=["light-0", "light-1"],
            known_coils=["0", "1", "2"])
    command_stream = stub.Start(configuration)
    asyncio.ensure_future(stub.SendSwitchChanges(switch_generator()))
    while True:
        command = await command_stream.read()
        print(command)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(connect())

import logging
import asyncio
import grpc
from grpc.experimental import aio

from mpf.platforms.visual_pinball_engine import platform_pb2_grpc
from mpf.platforms.visual_pinball_engine import platform_pb2


class MpfHardwareService(platform_pb2_grpc.MpfHardwareServiceServicer):

    async def Start(self, request, context):
        print("START")
        while True:
            command = platform_pb2.Commands()
            command.fade_light.common_fade_ms = 20
            fade = platform_pb2.FadeLightRequest.ChannelFade()
            fade.light_number = "1"
            fade.target_brightness = 0.5
            command.fade_light.fades.append(fade)
            yield command
            await asyncio.sleep(1)

    async def SendSwitchChanges(self, request_iterator, context):
        """Missing associated documentation comment in .proto file."""
        async for element in request_iterator:
            print(element)

    def Quit(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')



async def serve():
    server = aio.server()
    platform_pb2_grpc.add_MpfHardwareServiceServicer_to_server(MpfHardwareService(), server)
    listen_addr = '[::]:50051'
    server.add_insecure_port(listen_addr)
    logging.info("Starting server on %s", listen_addr)
    await server.start()
    await server.wait_for_termination()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())

"""Generate python files from protobufs."""
import glob
import re

from grpc_tools import protoc   # pylint: disable-msg=import-error


protoc.main([
    'grpc_tools.protoc',
    '--proto_path=protobuf/',
    '--python_out=.',
    '--grpc_python_out=.'
] + list(glob.iglob('./protobuf/*.proto')))

# Make pb2 imports in generated scripts relative
for script in glob.iglob('./*_pb2*.py'):
    with open(script, 'r+') as file:
        code = file.read()
        file.seek(0)
        file.write(re.sub(r'\n(import .+_pb2.*)', '\nfrom . \\1', code))
        file.truncate()

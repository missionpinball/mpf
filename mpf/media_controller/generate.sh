python3 -m grpc_tools.protoc -I../../../mc-rust/mpf-mc-rust/proto --python_out=. --grpc_python_out=. ../../../mc-rust/mpf-mc-rust/proto/server.proto
sed -i 's/import server_pb2 as server__pb2/from . import server_pb2 as server__pb2/' server_pb2_grpc.py

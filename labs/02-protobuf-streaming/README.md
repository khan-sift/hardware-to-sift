# 02 - Protobuf streaming (raw gRPC)

Mechanism: stream arbitrary protocol buffers over gRPC. No high-level wrapper exists in `sift_client` or `sift_py`, so this lab uses the generated `IngestService` stub directly. It is the lower-level path the convenience clients build on.

## Files
- `stream_protobuf.py` - streams `DroneState` messages via `IngestArbitraryProtobufDataStream`.
- `drone_state.proto` - the sample message.
- `drone_state_pb2.py` - pre-compiled, so no protoc needed. Regenerate with `python -m grpc_tools.protoc -I. --python_out=. drone_state.proto` if you change the proto.

## Run
```bash
pip install "sift-stack-py>=0.17" grpcio
export SIFT_API_KEY=...
export SIFT_BASE_URI=...
python stream_protobuf.py
```

## The six steps
1. When to use: you already emit protobuf and want to stream it as-is, or you need a lower-level path than config-based streaming.
2. Prerequisites: API key, base URI, a compiled protobuf message.
3. Schema: Sift must know your protobuf schema to map fields to channels. The stream carries only a type identifier and raw bytes, so the schema is registered out-of-band. Confirm that registration step for your environment before relying on this lab.
4. Ingest: build an `IngestArbitraryProtobufDataStreamRequest` per message and client-stream them through the `IngestService` stub.
5. Verify: open the asset in Sift and confirm channels appear for the protobuf fields.
6. Failure modes: unregistered or unknown message type, schema mismatch, missing timestamp.

## Validation status
Offline-validated: the proto compiles, the message serializes, the request builds, and the stub is present. The schema-registration semantics and the live stream are unverified, so this lab is intentionally lower-confidence than 01, 03, and 04.

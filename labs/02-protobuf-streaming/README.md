# 02 - Protobuf streaming (raw gRPC)

Mechanism: stream arbitrary protocol buffers over gRPC. No high-level wrapper
exists in `sift_client` or `sift_py`, so this lab uses the generated stubs
directly. It is the lower-level path the convenience clients build on.

## Files
- `stream_protobuf.py` - registers the schema, then streams `DroneState`
  messages via `IngestArbitraryProtobufDataStream`.
- `drone_state.proto` - the sample message.
- `drone_state_pb2.py` - pre-compiled, so no protoc needed. Regenerate with
  `python -m grpc_tools.protoc -I. --python_out=. drone_state.proto` if you
  change the proto.

## Run
```powershell
pip install "sift-stack-py[sift-stream]==0.17.0"
$env:SIFT_API_KEY  = "your-key"
$env:SIFT_BASE_URI = "grpc-api.development.siftstack.com"   # gRPC host; scheme optional
python stream_protobuf.py
```

## How schema registration works
This is the part that distinguishes the protobuf path. The stream request carries
only a message-type identifier and serialized bytes, no schema. Sift decodes the
bytes using a descriptor you register first, out of band:

1. Compile the proto and serialize it (with its dependencies) into a
   `FileDescriptorSet`. The script does this from the compiled module, so no
   protoc is needed at runtime.
2. Register it with `ProtobufDescriptorService.AddProtobufDescriptor`, passing a
   `ProtobufDescriptor{ message_type_full_name, file_descriptor_set,
   proto_file_name }`. Use `force_duplicate_registration=true` for idempotent
   re-runs.
3. Stream `IngestArbitraryProtobufDataStreamRequest` messages whose
   `message_type_identifier` matches the registered `message_type_full_name`.

Sift maps the message's scalar fields to channels automatically (`roll`,
`pitch`, `yaw`, `battery_v` here). Field behavior is tunable with custom proto
options in `sift.protobuf_descriptors.v2`, attached to fields in the `.proto`:
- `(units) = "rad"` - channel unit
- `(description) = "..."` - channel description
- `(ignore_field) = true` - exclude a field from becoming a channel

plus tag, map-key, array-index, and bytes-decoding controls. This lab keeps the
proto plain to validate the core path; annotating with units is the natural next
enhancement.

The authenticated channel comes from `sift_py`'s `use_sift_channel`, because the
raw protobuf path has no `sift_client` equivalent.

## Failure modes
- Streaming a `message_type_identifier` that was never registered.
- Descriptor mismatch between the registered schema and the serialized bytes.
- Missing or non-UTC timestamp.

## Validation status
Offline-validated: the proto compiles, the `FileDescriptorSet` builds, both the
registration request and the stream request build, and both stubs plus the
channel helper import. The live run confirms the registration is accepted and
the fields land as channels.

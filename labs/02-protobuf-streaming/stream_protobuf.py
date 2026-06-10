#!/usr/bin/env python3
"""
Lab 02: protobuf streaming (raw gRPC), with schema registration.

"Stream arbitrary protocol buffers to Sift" has no high-level wrapper in either
sift_client or sift_py, so this lab drops to the generated gRPC stubs. That is
the point: it shows the lower-level path the convenience clients sit on.

The stream request carries only a message-type identifier and serialized bytes,
no schema. Sift decodes those bytes using a protobuf descriptor you register
out of band, first, via ProtobufDescriptorService.AddProtobufDescriptor. That
registration step is what this lab adds and validates.

    1. register: drone_state.proto -> FileDescriptorSet -> AddProtobufDescriptor
    2. stream:   DroneState messages -> IngestArbitraryProtobufDataStream -> Sift

Sift maps the message's scalar fields to channels automatically (roll, pitch,
yaw, battery_v here). Field behavior is tunable with custom proto options in the
sift.protobuf_descriptors.v2 package, e.g. (units) = "rad", (description) = ...,
or (ignore_field) = true. This lab keeps the proto plain to validate the core
path; annotating fields with units is the natural next enhancement.

The authenticated channel comes from sift_py's use_sift_channel, because the raw
protobuf path has no sift_client equivalent. Everything else is hand-built.

Validation status: registration request, FileDescriptorSet construction, and the
stream request are validated offline against the installed sift stubs. The live
run confirms registration is accepted and the fields land as channels.

Setup:
    pip install "sift-stack-py[sift-stream]==0.17.0"
    # drone_state_pb2.py ships pre-compiled; to regenerate:
    #   pip install grpcio-tools
    #   python -m grpc_tools.protoc -I. --python_out=. drone_state.proto
    $env:SIFT_API_KEY  = "your-key"
    $env:SIFT_BASE_URI = "grpc-api.development.siftstack.com"   # gRPC host; scheme optional
Run:
    python stream_protobuf.py
"""

import math
import os
import time
from datetime import datetime, timezone

from google.protobuf import descriptor_pb2
from google.protobuf.timestamp_pb2 import Timestamp

import drone_state_pb2 as ds
from sift.ingest.v1 import ingest_pb2 as ing
from sift.ingest.v1.ingest_pb2_grpc import IngestServiceStub
from sift.protobuf_descriptors.v2 import protobuf_descriptors_pb2 as pd
from sift.protobuf_descriptors.v2.protobuf_descriptors_pb2_grpc import (
    ProtobufDescriptorServiceStub,
)
from sift_py.grpc.transport import SiftChannelConfig, use_sift_channel

ASSET_NAME = os.getenv("PROTO_ASSET_NAME", "protobuf-smoke")
MESSAGE_TYPE = ds.DroneState.DESCRIPTOR.full_name  # "drone.v1.DroneState"


def build_file_descriptor_set(file_desc) -> bytes:
    """Serialize a file descriptor and all its transitive dependencies."""
    fds = descriptor_pb2.FileDescriptorSet()
    seen = set()

    def add(fd):
        if fd.name in seen:
            return
        seen.add(fd.name)
        for dep in fd.dependencies:
            add(dep)
        fd.CopyToProto(fds.file.add())

    add(file_desc)
    return fds.SerializeToString()


def register_descriptor(channel) -> None:
    stub = ProtobufDescriptorServiceStub(channel)
    request = pd.AddProtobufDescriptorRequest(
        protobuf_descriptor=pd.ProtobufDescriptor(
            message_type_full_name=MESSAGE_TYPE,
            file_descriptor_set=build_file_descriptor_set(ds.DESCRIPTOR),
            proto_file_name="drone_state.proto",
        ),
        force_duplicate_registration=True,  # idempotent re-runs
    )
    response = stub.AddProtobufDescriptor(request)
    desc = response.protobuf_descriptor
    print(f"Registered descriptor: {desc.message_type_full_name} (id {desc.protobuf_descriptor_id})")


def request_stream(n: int = 200):
    """Yield one IngestArbitraryProtobufDataStreamRequest per tick."""
    for i in range(n):
        state = ds.DroneState(
            roll=0.5 * math.sin(i / 10),
            pitch=0.5 * math.cos(i / 10),
            yaw=(i / n) * math.pi,
            battery_v=12.6 - i * 0.005,
        )
        ts = Timestamp()
        ts.FromDatetime(datetime.now(timezone.utc))
        yield ing.IngestArbitraryProtobufDataStreamRequest(
            message_type_identifier=MESSAGE_TYPE,
            message_type_display_name="DroneState",
            asset_name=ASSET_NAME,
            timestamp=ts,
            value=state.SerializeToString(),
        )
        if (i + 1) % 20 == 0:
            print(f"[{i + 1}] streamed")
        time.sleep(0.05)


def main() -> None:
    creds: SiftChannelConfig = {
        "apikey": os.environ["SIFT_API_KEY"],
        "uri": os.environ.get("SIFT_BASE_URI") or os.environ["SIFT_GRPC_URL"],
    }
    with use_sift_channel(creds) as channel:
        register_descriptor(channel)
        ingest = IngestServiceStub(channel)
        print(f"Streaming arbitrary protobuf (DroneState) to '{ASSET_NAME}'. Ctrl-C to stop.")
        response = ingest.IngestArbitraryProtobufDataStream(request_stream())
        print("Stream complete. Response:", response)
        print(f"Done. Open the '{ASSET_NAME}' asset in Sift.")


if __name__ == "__main__":
    main()

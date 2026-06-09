#!/usr/bin/env python3
"""
Lab 02: protobuf streaming (raw gRPC).

This mechanism, "stream arbitrary protocol buffers to Sift over gRPC," has no
high-level wrapper in either sift_client or sift_py, so this lab drops to the
generated gRPC stub directly. That is the point of the lab: showing the
lower-level path the convenience clients sit on top of.

    your protobuf message --(serialize)--> IngestArbitraryProtobufDataStream --> Sift

Validation status (against the installed sift gRPC stubs):
    Validated offline: drone_state.proto compiles; DroneState serializes; and
    IngestArbitraryProtobufDataStreamRequest builds with the serialized payload,
    a Timestamp, the asset name, and a message type identifier.
    NOT validated, and the thing to confirm first: how Sift maps your arbitrary
    protobuf into channels. The stream request carries only a type identifier and
    the raw bytes, with no descriptor, so Sift must know the schema out-of-band.
    Confirm the schema-registration step for your environment before relying on
    this lab (Sift's protobuf-ingestion docs or console).

Setup:
    pip install "sift-stack-py>=0.17" grpcio
    # drone_state_pb2.py is shipped pre-compiled; to regenerate it:
    #   pip install grpcio-tools
    #   python -m grpc_tools.protoc -I. --python_out=. drone_state.proto

    export SIFT_API_KEY=...
    export SIFT_BASE_URI=...     # the sift_py transport used here takes a single uri
Run:
    python stream_protobuf.py
"""

import math
import os
import time
from datetime import datetime, timezone

from google.protobuf.timestamp_pb2 import Timestamp

import drone_state_pb2 as ds
from sift.ingest.v1 import ingest_pb2 as ing
from sift.ingest.v1.ingest_pb2_grpc import IngestServiceStub

# sift_py only supplies the authenticated gRPC channel; there is no sift_client
# equivalent for this raw path. The ingestion itself is hand-built protobuf.
from sift_py.grpc.transport import SiftChannelConfig, use_sift_channel

ASSET_NAME = os.getenv("PROTO_ASSET_NAME", "proto-drone-demo")
MESSAGE_TYPE = "drone.v1.DroneState"


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
        time.sleep(0.05)


def main() -> None:
    creds: SiftChannelConfig = {
        "apikey": os.environ["SIFT_API_KEY"],
        "uri": os.environ["SIFT_BASE_URI"],
    }
    with use_sift_channel(creds) as channel:
        stub = IngestServiceStub(channel)
        print("Streaming arbitrary protobuf (DroneState). Ctrl-C to stop.")
        response = stub.IngestArbitraryProtobufDataStream(request_stream())
        print("Stream complete. Response:", response)


if __name__ == "__main__":
    main()

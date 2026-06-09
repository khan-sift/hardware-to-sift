#!/usr/bin/env python3
"""
SITL -> Sift smoke test, sift_client edition.

Same goal as sitl_to_sift_smoketest.py, ported to the supported `sift_client`
module. The original uses `sift_py`, which is deprecated and removed at v1.0.0.
This streams PX4 / ArduPilot SITL attitude telemetry into Sift via
ingestion-config-based streaming over gRPC.

    SITL flight stack --(MAVLink / UDP)--> this script --(gRPC)--> Sift

Validation status (against sift-stack-py 0.17.0):
    Validated offline: all imports resolve; the streaming API
    (create_ingestion_config_streaming_client, send, finish) are coroutines;
    and IngestionConfigCreate, FlowConfig, ChannelConfig, ChannelValue, and Flow
    all construct correctly.
    Not yet validated: the live connection. On the first real run, confirm the
    client and event-loop interaction (see the note in main()).

Setup:
    pip install "sift-stack-py>=0.17" pymavlink

    Start SITL, for example:
        ArduPilot:  sim_vehicle.py -v ArduCopter --out=udp:127.0.0.1:14550
        PX4:        make px4_sitl jmavsim        (telemetry on udp:127.0.0.1:14540)

    export SIFT_API_KEY=...
    export SIFT_GRPC_URL=...     # gRPC endpoint for your environment
    export SIFT_REST_URL=...     # REST endpoint (optional)
    export MAVLINK_ENDPOINT=udp:127.0.0.1:14550   # optional, default shown
"""

import asyncio
import os
from datetime import datetime, timezone

from pymavlink import mavutil

from sift_client.client import SiftClient
from sift_client.resources import StreamingMode
from sift_client.sift_types.ingestion import (
    ChannelConfig,
    ChannelDataType,
    ChannelValue,
    Flow,
    FlowConfig,
    IngestionConfigCreate,
)

ASSET_NAME = "sitl-drone"
CONFIG_KEY = "sitl-drone-smoke-test-v1"
FLOW_NAME = "attitude"
MAVLINK_ENDPOINT = os.getenv("MAVLINK_ENDPOINT", "udp:127.0.0.1:14550")


def build_config() -> IngestionConfigCreate:
    """One flow, three attitude channels.

    Channel order here is the contract: the ChannelValue list in each Flow must
    name these same channels.
    """
    return IngestionConfigCreate(
        asset_name=ASSET_NAME,
        client_key=CONFIG_KEY,
        flows=[
            FlowConfig(
                name=FLOW_NAME,
                channels=[
                    ChannelConfig(name="attitude.roll", data_type=ChannelDataType.DOUBLE, unit="rad"),
                    ChannelConfig(name="attitude.pitch", data_type=ChannelDataType.DOUBLE, unit="rad"),
                    ChannelConfig(name="attitude.yaw", data_type=ChannelDataType.DOUBLE, unit="rad"),
                ],
            ),
        ],
    )


def connect_sitl():
    """Connect to the SITL MAVLink stream and wait for a heartbeat."""
    print(f"Connecting to SITL at {MAVLINK_ENDPOINT} ...")
    mav = mavutil.mavlink_connection(MAVLINK_ENDPOINT)
    mav.wait_heartbeat()
    print(f"Heartbeat received from system {mav.target_system}")
    return mav


async def main() -> None:
    api_key = os.environ["SIFT_API_KEY"]
    grpc_url = os.environ["SIFT_GRPC_URL"]
    rest_url = os.environ.get("SIFT_REST_URL")

    mav = connect_sitl()

    # NOTE: sift_client is async-first and manages its own event loop. If creating
    # the client inside this running loop conflicts on your version, construct it
    # before asyncio.run() and pass it in, or use the client's loop helpers.
    client = SiftClient(api_key=api_key, grpc_url=grpc_url, rest_url=rest_url)

    streaming = await client.ingestion.create_ingestion_config_streaming_client(
        build_config(),
        streaming_mode=StreamingMode.LIVE_ONLY,
    )
    print("Ingestion config registered. Streaming attitude. Ctrl-C to stop.")

    # recv_match is a blocking read; fine here since send is the only other work.
    sent = 0
    try:
        while True:
            msg = mav.recv_match(type="ATTITUDE", blocking=True, timeout=5)
            if msg is None:
                continue
            await streaming.send(Flow(
                flow=FLOW_NAME,
                timestamp=datetime.now(timezone.utc),
                channel_values=[
                    ChannelValue(name="attitude.roll", ty=ChannelDataType.DOUBLE, value=msg.roll),
                    ChannelValue(name="attitude.pitch", ty=ChannelDataType.DOUBLE, value=msg.pitch),
                    ChannelValue(name="attitude.yaw", ty=ChannelDataType.DOUBLE, value=msg.yaw),
                ],
            ))
            sent += 1
            print(f"[{sent}] roll={msg.roll:+.3f} pitch={msg.pitch:+.3f} yaw={msg.yaw:+.3f}")
    finally:
        await streaming.finish()


if __name__ == "__main__":
    asyncio.run(main())

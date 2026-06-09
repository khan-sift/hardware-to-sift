#!/usr/bin/env python3
"""
SITL -> Sift smoke test, sift_client edition.

Same goal as sitl_to_sift_smoketest.py, ported to the supported `sift_client`
module. Streams PX4 / ArduPilot SITL attitude telemetry into Sift via
ingestion-config-based streaming over gRPC.

    SITL flight stack --(MAVLink / UDP)--> this script --(gRPC)--> Sift

Two SDK facts this script follows (verified against sift-stack-py 0.17.0):
  - Ingestion is async-only and lives on `client.async_.ingestion`, not
    `client.ingestion`.
  - SiftClient runs its own background event loop, so the coroutine is driven
    with run_coroutine_threadsafe onto `client.get_asyncio_loop()` rather than
    asyncio.run. The blocking MAVLink read is offloaded to an executor so it does
    not stall that loop.

Validation status: imports, the async ingestion accessor, the client loop, and
config/flow/value construction are validated offline. The live stream is the
end-to-end check.

Setup:
    pip install "sift-stack-py>=0.17" pymavlink
    # Start SITL, e.g. ArduPilot: sim_vehicle.py -v ArduCopter --out=udp:127.0.0.1:14550
    export SIFT_API_KEY=...
    export SIFT_GRPC_URL=...
    export SIFT_REST_URL=...
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
    print(f"Connecting to SITL at {MAVLINK_ENDPOINT} ...")
    mav = mavutil.mavlink_connection(MAVLINK_ENDPOINT)
    mav.wait_heartbeat()
    print(f"Heartbeat received from system {mav.target_system}")
    return mav


async def stream(client: SiftClient, mav) -> None:
    streaming = await client.async_.ingestion.create_ingestion_config_streaming_client(
        build_config(),
        streaming_mode=StreamingMode.LIVE_ONLY,
    )
    print("Ingestion config registered. Streaming attitude. Ctrl-C to stop.")
    loop = asyncio.get_running_loop()
    sent = 0
    try:
        while True:
            # recv_match blocks, so run it off the event loop
            msg = await loop.run_in_executor(
                None, lambda: mav.recv_match(type="ATTITUDE", blocking=True, timeout=5)
            )
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


def main() -> None:
    mav = connect_sitl()
    client = SiftClient(
        api_key=os.environ["SIFT_API_KEY"],
        grpc_url=os.environ["SIFT_GRPC_URL"],
        rest_url=os.environ.get("SIFT_REST_URL"),
    )
    future = asyncio.run_coroutine_threadsafe(stream(client, mav), client.get_asyncio_loop())
    future.result()


if __name__ == "__main__":
    main()

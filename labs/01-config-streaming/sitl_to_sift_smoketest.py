#!/usr/bin/env python3
"""
SITL -> Sift smoke test.

Proves Sift ingestion mechanism #1 (ingestion-config-based streaming over gRPC)
carries real telemetry end to end, using a PX4 / ArduPilot SITL simulator as the
data source. No hardware and no flying required.

    SITL flight stack --(MAVLink / UDP)--> this script --(gRPC)--> Sift

Setup:
    pip install "sift-stack-py>=0.17,<1.0" pymavlink

    NOTE on SDK generations (validated 2026-06, sift-stack-py 0.17.0):
    This script uses the `sift_py` module, which is what Sift's public Python
    docs currently teach. As of v0.10.0 `sift_py` is deprecated in favor of the
    newer `sift_client` module and is scheduled for removal in v1.0.0. The pin
    above keeps `sift_py` available. For a long-lived tutorial, port this to
    `sift_client` once its streaming pattern is confirmed.

    Start a SITL instance that emits MAVLink, for example:
        ArduPilot:  sim_vehicle.py -v ArduCopter --out=udp:127.0.0.1:14550
        PX4:        make px4_sitl jmavsim        (telemetry on udp:127.0.0.1:14540)

    Provide credentials (never hard-code these):
        export SIFT_API_KEY=...     # Sift > Settings > API Keys
        export SIFT_BASE_URI=...    # your environment's gRPC URL
        export MAVLINK_ENDPOINT=udp:127.0.0.1:14550   # optional, this is the default
"""

import os
from datetime import datetime, timezone

from pymavlink import mavutil

from sift_py.grpc.transport import SiftChannelConfig, use_sift_channel
from sift_py.ingestion.channel import ChannelConfig, ChannelDataType, double_value
from sift_py.ingestion.config.telemetry import TelemetryConfig
from sift_py.ingestion.flow import FlowConfig
from sift_py.ingestion.service import IngestionService

ASSET_NAME = "sitl-drone"
CONFIG_KEY = "sitl-drone-smoke-test-v1"
MAVLINK_ENDPOINT = os.getenv("MAVLINK_ENDPOINT", "udp:127.0.0.1:14550")


def build_config() -> TelemetryConfig:
    """One flow, three attitude channels.

    Channel order here is a contract: the order of values passed to
    ingest_flows() below must match this exact order.
    """
    return TelemetryConfig(
        asset_name=ASSET_NAME,
        ingestion_client_key=CONFIG_KEY,
        flows=[
            FlowConfig(
                name="attitude",
                channels=[
                    ChannelConfig(name="attitude.roll", data_type=ChannelDataType.DOUBLE, unit="rad"),
                    ChannelConfig(name="attitude.pitch", data_type=ChannelDataType.DOUBLE, unit="rad"),
                    ChannelConfig(name="attitude.yaw", data_type=ChannelDataType.DOUBLE, unit="rad"),
                ],
            ),
        ],
    )


def main() -> None:
    api_key = os.environ["SIFT_API_KEY"]
    base_uri = os.environ["SIFT_BASE_URI"]

    # 1. Source: connect to the SITL MAVLink stream and wait for a heartbeat.
    print(f"Connecting to SITL at {MAVLINK_ENDPOINT} ...")
    mav = mavutil.mavlink_connection(MAVLINK_ENDPOINT)
    mav.wait_heartbeat()
    print(f"Heartbeat received from system {mav.target_system}")

    # 2. Sink: open the Sift gRPC channel and register the ingestion config.
    config = build_config()
    credentials: SiftChannelConfig = {"apikey": api_key, "uri": base_uri}

    with use_sift_channel(credentials) as channel:
        ingestion_service = IngestionService(channel, config)
        print("Ingestion config registered. Streaming attitude. Ctrl-C to stop.")

        # 3. Pump: read each ATTITUDE message and stream it as one flow row.
        sent = 0
        while True:
            msg = mav.recv_match(type="ATTITUDE", blocking=True, timeout=5)
            if msg is None:
                continue
            ingestion_service.ingest_flows({
                "flow_name": "attitude",
                "timestamp": datetime.now(timezone.utc),
                "channel_values": [
                    double_value(msg.roll),
                    double_value(msg.pitch),
                    double_value(msg.yaw),
                ],
            })
            sent += 1
            print(f"[{sent}] roll={msg.roll:+.3f} pitch={msg.pitch:+.3f} yaw={msg.yaw:+.3f}")


if __name__ == "__main__":
    main()

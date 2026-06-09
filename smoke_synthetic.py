#!/usr/bin/env python3
"""
Synthetic smoke test: stream a sine wave into Sift with no SITL, no MAVLink, and
no hardware. The fastest way to confirm your credentials and the ingestion
pipeline work end to end.

Uses the sift_py (synchronous) path, the documented and battle-tested one, to
keep the number of variables minimal for a first green. Once this lands data,
the SITL-based labs differ only in where the numbers come from.

Setup (PowerShell):
    pip install "sift-stack-py<1.0"
    $env:SIFT_API_KEY = "your-key"
    $env:SIFT_BASE_URI = "grpc-api.development.siftstack.com"
    python smoke_synthetic.py

Setup (bash / WSL):
    pip install "sift-stack-py<1.0"
    export SIFT_API_KEY=your-key
    export SIFT_BASE_URI=grpc-api.development.siftstack.com
    python smoke_synthetic.py
"""

import math
import os
import time
from datetime import datetime, timezone

from sift_py.grpc.transport import SiftChannelConfig, use_sift_channel
from sift_py.ingestion.channel import ChannelConfig, ChannelDataType, double_value
from sift_py.ingestion.config.telemetry import TelemetryConfig
from sift_py.ingestion.flow import FlowConfig
from sift_py.ingestion.service import IngestionService

ASSET_NAME = "synthetic-smoke"
CONFIG_KEY = "synthetic-smoke-v1"


def build_config() -> TelemetryConfig:
    return TelemetryConfig(
        asset_name=ASSET_NAME,
        ingestion_client_key=CONFIG_KEY,
        flows=[
            FlowConfig(
                name="signal",
                channels=[ChannelConfig(name="sine.value", data_type=ChannelDataType.DOUBLE, unit="V")],
            ),
        ],
    )


def main() -> None:
    creds: SiftChannelConfig = {
        "apikey": os.environ["SIFT_API_KEY"],
        "uri": os.environ["SIFT_BASE_URI"],
    }
    with use_sift_channel(creds) as channel:
        service = IngestionService(channel, build_config())
        print("Connected. Streaming a sine wave to asset 'synthetic-smoke'. Ctrl-C to stop.")
        for i in range(200):
            service.ingest_flows({
                "flow_name": "signal",
                "timestamp": datetime.now(timezone.utc),
                "channel_values": [double_value(math.sin(i / 10))],
            })
            print(f"[{i + 1}] sine={math.sin(i / 10):+.3f}")
            time.sleep(0.1)
        print("Done. Open the 'synthetic-smoke' asset in Sift to see the sine.value channel.")


if __name__ == "__main__":
    main()

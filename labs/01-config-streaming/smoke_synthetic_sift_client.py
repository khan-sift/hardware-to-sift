#!/usr/bin/env python3
"""
Synthetic smoke test for the sift_client (async) path. No SITL, no hardware.
Confirms the supported client end to end and settles how its event loop is driven.

Two things the SDK forces here, both verified against sift-stack-py 0.17.0:
  - Ingestion is async-only and lives on `client.async_.ingestion`. The sync
    client has no `ingestion` accessor.
  - SiftClient runs its own background event loop. Drive the coroutine with
    run_coroutine_threadsafe onto `client.get_asyncio_loop()`, not asyncio.run,
    which would bind the gRPC channel to a different loop.

Setup (PowerShell):
    pip install sift-stack-py
    $env:SIFT_API_KEY = "your-key"
    $env:SIFT_GRPC_URL = "https://grpc-api.development.siftstack.com"
    $env:SIFT_REST_URL = "https://api.development.siftstack.com"
    python smoke_synthetic_sift_client.py
"""

import asyncio
import math
import os
from datetime import datetime, timezone

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

ASSET_NAME = "synthetic-smoke-sift-client"
CONFIG_KEY = "synthetic-smoke-sc-v1"
FLOW_NAME = "signal"


def build_config() -> IngestionConfigCreate:
    return IngestionConfigCreate(
        asset_name=ASSET_NAME,
        client_key=CONFIG_KEY,
        flows=[
            FlowConfig(
                name=FLOW_NAME,
                channels=[ChannelConfig(name="sine.value", data_type=ChannelDataType.DOUBLE, unit="V")],
            ),
        ],
    )


async def stream(client: SiftClient) -> None:
    streaming = await client.async_.ingestion.create_ingestion_config_streaming_client(
        build_config(),
        streaming_mode=StreamingMode.LIVE_ONLY,
    )
    print("Connected. Streaming a sine wave to 'synthetic-smoke-sift-client'. Ctrl-C to stop.")
    try:
        for i in range(200):
            await streaming.send(Flow(
                flow=FLOW_NAME,
                timestamp=datetime.now(timezone.utc),
                channel_values=[ChannelValue(name="sine.value", ty=ChannelDataType.DOUBLE, value=math.sin(i / 10))],
            ))
            print(f"[{i + 1}] sine={math.sin(i / 10):+.3f}")
            await asyncio.sleep(0.1)
    finally:
        await streaming.finish()
    print("Done. Open the 'synthetic-smoke-sift-client' asset in Sift.")


def main() -> None:
    client = SiftClient(
        api_key=os.environ["SIFT_API_KEY"],
        grpc_url=os.environ["SIFT_GRPC_URL"],
        rest_url=os.environ.get("SIFT_REST_URL"),
    )
    # Ingestion is async-only; run it on the client's own loop and block for the result.
    future = asyncio.run_coroutine_threadsafe(stream(client), client.get_asyncio_loop())
    future.result()


if __name__ == "__main__":
    main()

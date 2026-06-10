#!/usr/bin/env python3
"""
Lab 04: CAN / DBC decode and stream via sift_client.

Mirrors the `can_example` shape seen in the dev environment: raw CAN frames are
decoded against a DBC file into named signals, and each signal becomes a Sift
channel named MESSAGE.signal. One Sift flow per CAN message. This is the shape
you would also use for DroneCAN / UAVCAN on the capstone drone.

    raw CAN frame --(DBC decode)--> named signals --(gRPC streaming)--> Sift

Self-contained: it writes a small sample DBC and synthesizes frames, so no bus
or hardware is needed. Point it at a real DBC and a real CAN log to go live.

Two SDK facts this follows (same as lab 01, verified against sift-stack-py 0.17.0):
  - Ingestion is async-only and lives on `client.async_.ingestion`.
  - SiftClient runs its own background loop, so the coroutine is driven with
    run_coroutine_threadsafe onto `client.get_asyncio_loop()`, not asyncio.run.

Validation status (against sift-stack-py 0.17.0 and cantools):
    Validated offline: the sample DBC loads; encode/decode round-trips; the
    per-message ingestion config builds; ChannelValue / Flow construct; and the
    call uses the correct async accessor. The live stream is the end-to-end check.

Setup:
    pip install "sift-stack-py[sift-stream]==0.17.0" cantools
    $env:SIFT_API_KEY  = "your-key"
    $env:SIFT_GRPC_URL = "https://grpc-api.development.siftstack.com"
    $env:SIFT_REST_URL = "https://api.development.siftstack.com"
Run:
    python decode_can_and_stream.py
"""

import asyncio
import math
import os
from datetime import datetime, timezone
from pathlib import Path

import cantools

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

ASSET_NAME = os.getenv("CAN_ASSET_NAME", "can-bus-demo")
CONFIG_KEY = "can-bus-demo-v1"
HERE = Path(__file__).parent
DBC_PATH = HERE / "sample.dbc"

SAMPLE_DBC = '''VERSION ""

NS_ :

BS_:

BU_: ECU

BO_ 256 MOTOR_STATUS: 8 ECU
 SG_ speed_kph : 0|16@1+ (0.1,0) [0|6553.5] "kph" ECU
 SG_ motor_temp : 16|8@1+ (1,-40) [-40|215] "degC" ECU

BO_ 257 BATT_STATUS: 8 ECU
 SG_ BATT_Voltage : 0|16@1+ (0.01,0) [0|655.35] "V" ECU
 SG_ BATT_Current : 16|16@1- (0.1,0) [-3276.8|3276.7] "A" ECU
'''


def load_dbc() -> "cantools.database.Database":
    if not DBC_PATH.exists():
        DBC_PATH.write_text(SAMPLE_DBC)
        print(f"wrote {DBC_PATH.name}")
    return cantools.database.load_file(DBC_PATH)


def build_config(db) -> IngestionConfigCreate:
    """One flow per CAN message; channels are the message's signals, named
    MESSAGE.signal to match how decoded CAN appears in Sift."""
    flows = []
    for msg in db.messages:
        flows.append(FlowConfig(
            name=msg.name,
            channels=[
                ChannelConfig(
                    name=f"{msg.name}.{sig.name}",
                    data_type=ChannelDataType.DOUBLE,
                    unit=sig.unit or "",
                )
                for sig in msg.signals
            ],
        ))
    return IngestionConfigCreate(asset_name=ASSET_NAME, client_key=CONFIG_KEY, flows=flows)


def synthesize(msg_name: str, i: int) -> dict:
    """Fake but in-range signal values for one message at tick i."""
    if msg_name == "MOTOR_STATUS":
        return {"speed_kph": round(40 + 10 * math.sin(i / 10), 1), "motor_temp": 30 + (i % 50)}
    if msg_name == "BATT_STATUS":
        return {"BATT_Voltage": round(12.6 - i * 0.01, 2), "BATT_Current": round(5 * math.sin(i / 8), 1)}
    return {}


async def stream(client: SiftClient, db) -> None:
    streaming = await client.async_.ingestion.create_ingestion_config_streaming_client(
        build_config(db),
        streaming_mode=StreamingMode.LIVE_ONLY,
    )
    print("Ingestion config registered. Streaming decoded CAN. Ctrl-C to stop.")
    try:
        for i in range(200):
            for msg in db.messages:
                values = synthesize(msg.name, i)
                # round-trip through the DBC so the lab exercises real decoding
                raw = msg.encode(values)
                decoded = db.decode_message(msg.frame_id, raw)
                await streaming.send(Flow(
                    flow=msg.name,
                    timestamp=datetime.now(timezone.utc),
                    channel_values=[
                        ChannelValue(
                            name=f"{msg.name}.{sig.name}",
                            ty=ChannelDataType.DOUBLE,
                            value=float(decoded[sig.name]),
                        )
                        for sig in msg.signals
                    ],
                ))
            if (i + 1) % 40 == 0:
                print(f"[{i + 1}] ticks streamed")
            await asyncio.sleep(0.05)
        print("Done streaming 200 ticks per message.")
    finally:
        await streaming.finish()


def main() -> None:
    client = SiftClient(
        api_key=os.environ["SIFT_API_KEY"],
        grpc_url=os.environ["SIFT_GRPC_URL"],
        rest_url=os.environ.get("SIFT_REST_URL"),
    )
    db = load_dbc()
    # Ingestion is async-only; run it on the client's own loop.
    future = asyncio.run_coroutine_threadsafe(stream(client, db), client.get_asyncio_loop())
    future.result()


if __name__ == "__main__":
    main()

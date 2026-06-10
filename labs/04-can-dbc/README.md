# 04 - CAN / DBC

Mechanism: config-based streaming with a CAN/DBC decode step in front. Raw CAN frames are decoded against a DBC into named signals; each signal becomes a Sift channel named `MESSAGE.signal`, with one flow per CAN message. Same shape as the dev env's `can_example`, and the path you would use for DroneCAN / UAVCAN on the capstone drone.

## Script
`decode_can_and_stream.py` writes a small sample DBC and synthesizes frames, so it runs with no bus or hardware. Point it at a real DBC and CAN log to go live.

## Run
```powershell
pip install "sift-stack-py[sift-stream]==0.17.0" cantools
$env:SIFT_API_KEY  = "your-key"
$env:SIFT_GRPC_URL = "https://grpc-api.development.siftstack.com"
$env:SIFT_REST_URL = "https://api.development.siftstack.com"
python decode_can_and_stream.py
```

## The six steps
1. When to use: telemetry arriving as CAN frames described by a DBC. Decode first, then stream.
2. Prerequisites: API key, gRPC URL, a DBC file (a sample is generated here).
3. Schema: one flow per CAN message; channels are the message's signals, with units taken from the DBC.
4. Ingest: decode each frame with cantools, then send a Flow per message via the streaming client.
5. Verify: open the Run in Sift and confirm the `MESSAGE.signal` channels and their DBC units.
6. Failure modes: values outside the DBC's declared range, channel names not matching the config, and enum signals (DBC value tables) that need ENUM rather than DOUBLE.

## Validation status
Offline-validated against sift-stack-py 0.17.0 and cantools: DBC load, encode/decode round-trip, config build, and value construction. The live stream is the first real end-to-end check.

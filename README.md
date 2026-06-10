# Hardware to Sift

A tutorial and a set of runnable labs that trace telemetry from a physical sensor all the way into Sift, covering every common ingestion path. Built and validated end to end rather than from memory.

## What is inside

- `docs/hardware-to-sift-framework.md` - the framework that drives the tutorial. Every path and format carries a validation status.
- `labs/` - one lab per ingestion mechanism, sharing a six-step template.
- `capstone-drone/` - a real drone build that exercises the paths end to end.

## Status

| Lab | Mechanism | State |
|---|---|---|
| 01 | Config-based streaming | Built (sift_py + sift_client), live-validated end to end |
| 02 | Protobuf streaming | Built and live-validated (schema registration + arbitrary protobuf) |
| 03 | Data import (CSV, then Parquet) | Built and live-validated (both jobs succeeded) |
| 04 | CAN / DBC | Built and offline-validated |
| 05 | Schemaless JSON over REST and Influx | To do (no in-house reference yet) |

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export SIFT_API_KEY=...     # from Sift > Settings > API Keys
export SIFT_BASE_URI=...    # your environment's gRPC URL
```

Never commit credentials. `.env` and key files are git-ignored.

## SDK note

Sift's public Python docs teach the `sift_py` module, which is deprecated as of v0.10.0 and removed at v1.0.0. The forward path is `sift_client`. The pin in `requirements.txt` keeps `sift_py` working until the labs are ported. See Section 5 of the framework.

## A caution before making this public

The framework currently references an internal Sift dev environment, including real counts and asset names. Keep this repo private, or sanitize `docs/hardware-to-sift-framework.md` before publishing.

## Validation provenance

Sift docs, a read-only Sift dev environment, and sift-stack-py 0.17.0, as of 2026-06-09.

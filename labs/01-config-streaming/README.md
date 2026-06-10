# 01 - Config-based streaming

The lead ingestion path: define a schema (an ingestion config), then stream
structured rows over gRPC. This is what the Sift client libraries wrap and what
most in-house ingestion uses.

## Scripts
Two SDK modules, two scripts each (a no-hardware synthetic test and a SITL test):

- `smoke_synthetic_sift_client.py` - **start here.** Supported `sift_client`
  module (async). Streams a synthetic sine wave, no SITL or hardware needed.
- `stream_attitude_sift_client.py` - `sift_client` module against a PX4 or
  ArduPilot SITL simulator. Target this pattern going forward.
- `smoke_synthetic.py` - legacy `sift_py` module, synthetic sine, no hardware.
- `sitl_to_sift_smoketest.py` - legacy `sift_py` module against SITL. Kept to
  show the migration from the deprecated path.

`sift_py` is deprecated as of v0.10.0 and removed at v1.0.0. The `sift_client`
scripts are the ones to build on.

## Install
Use a per-project virtual environment. The `sift_client` streaming path needs
the `[sift-stream]` extra (native `sift_stream_bindings`); the `sift_py` path
does not, but installing the extra satisfies both.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install "sift-stack-py[sift-stream]==0.17.0"
```

## Run
No SITL required for the synthetic test:
```powershell
$env:SIFT_API_KEY  = "your-key"
$env:SIFT_GRPC_URL = "https://grpc-api.development.siftstack.com"
$env:SIFT_REST_URL = "https://api.development.siftstack.com"
.\.venv\Scripts\python.exe smoke_synthetic_sift_client.py
```
The SITL scripts additionally need a running simulator and `pymavlink`. The
legacy `sift_py` scripts read `SIFT_API_KEY` and `SIFT_BASE_URI` (a bare host)
instead of the split grpc/rest URLs.

## Two SDK facts the sift_client scripts depend on
Both verified live against sift-stack-py 0.17.0:
- Ingestion is async-only and lives on `client.async_.ingestion`. The sync
  client has no `ingestion` accessor.
- `SiftClient` runs its own background event loop. The scripts drive the
  coroutine with `run_coroutine_threadsafe` onto `client.get_asyncio_loop()`
  rather than `asyncio.run`, which would bind the gRPC channel to a different
  loop.

## Validation status
Live-confirmed end to end on 2026-06-09 against the dev environment:
- `sift_py` path (`smoke_synthetic.py`): the `sine.value` channel on the
  `synthetic-smoke` asset renders the expected sine in the Sift UI.
- `sift_client` path (`smoke_synthetic_sift_client.py`): the `sine.value`
  channel on the `synthetic-smoke-sift-client` asset renders correctly, with the
  native `sift_stream` task reporting a clean shutdown.

The two SITL scripts share the same config and streaming calls as their
synthetic counterparts; they are validated offline (imports, config build, the
streaming call) and exercised live through the synthetic tests. A full SITL run
with real flight data is the capstone.

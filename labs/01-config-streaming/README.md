# 01 - Config-based streaming

The lead ingestion path: define a schema, then stream structured rows over gRPC. Both scripts use a PX4 or ArduPilot SITL simulator as the source, so no hardware is required.

## Scripts
- `stream_attitude_sift_client.py` - primary. Uses the supported `sift_client` module (async). Target this going forward.
- `sitl_to_sift_smoketest.py` - legacy reference. Uses the deprecated `sift_py` module (removed at v1.0.0). Kept to show the migration.

## Run
Start a SITL instance, then set credentials and run the primary script:
```bash
export SIFT_API_KEY=...
export SIFT_GRPC_URL=...        # sift_client uses separate grpc and rest URLs
export SIFT_REST_URL=...        # optional
python stream_attitude_sift_client.py
```
The legacy script instead reads `SIFT_API_KEY` and `SIFT_BASE_URI`.

## Validation status
Both scripts are validated offline against sift-stack-py 0.17.0: imports resolve, the streaming API calls exist, and the ingestion config builds. Neither has been run against a live Sift environment yet. On the first live run, confirm data lands, and for the sift_client version confirm the client and event-loop interaction.

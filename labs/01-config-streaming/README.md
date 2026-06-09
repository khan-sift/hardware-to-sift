# 01 - Config-based streaming

The lead ingestion path. `sitl_to_sift_smoketest.py` proves it end to end using a PX4 or ArduPilot SITL simulator as the source, with no hardware required.

Run a SITL instance, set `SIFT_API_KEY` and `SIFT_BASE_URI`, then:

```bash
python sitl_to_sift_smoketest.py
```

Open item: port from `sift_py` to `sift_client`.

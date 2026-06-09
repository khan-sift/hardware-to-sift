# 03 - Data import (CSV and Parquet)

Mechanism: data import, batch upload of recorded files. Synchronous, unlike streaming. CSV and Parquet are the two highest-volume confirmed import formats.

## Script
`import_csv_and_parquet.py` generates small sample files (flat schema, one column per channel) and imports each into Sift, creating a Run you can open.

## Run
```bash
pip install "sift-stack-py>=0.17"
pip install pandas pyarrow        # only to regenerate the sample files
export SIFT_API_KEY=...
export SIFT_GRPC_URL=...
export SIFT_REST_URL=...           # data import uses the REST endpoint
python import_csv_and_parquet.py
```

## The six steps
1. When to use: recorded files in a confirmed format (CSV, Parquet, HDF5, TDMS, Chapter 10). Not for live data, use lab 01. Not for MCAP, uLog, MDF, or ROS, which do not import natively.
2. Prerequisites: API key, gRPC and REST URLs.
3. Schema: CSV needs a header row and a timestamp column. Parquet must be flat, one channel per column. The script declares each channel explicitly; `detect_config()` is the auto-detect alternative.
4. Ingest: `client.data_imports.import_from_path(path, config=...)`.
5. Verify: open the resulting Run in Sift and confirm the channels and values.
6. Failure modes: unsupported or empty timestamps, wrong CSV column numbering, non-flat Parquet.

## Validation status
Offline-validated against sift-stack-py 0.17.0: imports, sample generation, explicit config construction, and the import method signature. The live upload is the first real end-to-end check.

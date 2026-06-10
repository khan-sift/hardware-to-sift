# 03 - Data import (CSV and Parquet)

Mechanism: data import, batch upload of recorded files. Synchronous, unlike streaming. CSV and Parquet are the two highest-volume confirmed import formats.

## Script
`import_csv_and_parquet.py` generates small sample files (flat schema, one column per channel) and imports each into Sift, creating a Run you can open.

## Run
```powershell
pip install "sift-stack-py==0.17.0"
pip install pandas pyarrow        # only to regenerate the sample files
$env:SIFT_API_KEY  = "your-key"
$env:SIFT_GRPC_URL = "https://grpc-api.development.siftstack.com"
$env:SIFT_REST_URL = "https://api.development.siftstack.com"   # import uses REST
python import_csv_and_parquet.py
```

## The six steps
1. When to use: recorded files in a confirmed format (CSV, Parquet, HDF5, TDMS, Chapter 10). Not for live data, use lab 01. Not for MCAP, uLog, MDF, or ROS, which do not import natively.
2. Prerequisites: API key, gRPC and REST URLs.
3. Schema: CSV needs a header row and a timestamp column. Parquet must be flat, one channel per column. The script declares each channel explicitly; `detect_config()` is the auto-detect alternative.
4. Ingest: `client.data_import.import_from_path(path, config=...)` (synchronous; note the singular `data_import`).
5. Verify: open the resulting Run in Sift and confirm the channels and values.
6. Failure modes: unsupported or empty timestamps, wrong CSV column numbering, non-flat Parquet.

## Validation status
Offline-validated against sift-stack-py 0.17.0: imports, sample generation, explicit config construction, and the import method signature. The live upload is the first real end-to-end check.

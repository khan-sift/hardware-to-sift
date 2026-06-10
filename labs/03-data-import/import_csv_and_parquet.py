#!/usr/bin/env python3
"""
Lab 03: data import (CSV, then Parquet) via sift_client.

Demonstrates Sift ingestion mechanism "data import" for the two highest-volume,
confirmed formats. Unlike streaming, this path is synchronous.

    recorded file (CSV / Parquet) --(REST upload)--> Sift  -> a Run you can open

Validation status (against sift-stack-py 0.17.0):
    Validated offline: imports resolve; the sample-data generator writes valid
    CSV and Parquet; DataTypeKey and TimeFormat values are real; the explicit
    CsvImportConfig / ParquetFlatDatasetImportConfig objects construct; and the
    call uses the correct synchronous accessor, client.data_import (singular).
    Column numbers are 1-indexed, matching the SDK's first_data_row convention.
    The live upload is the end-to-end check.

Setup:
    pip install "sift-stack-py==0.17.0"
    pip install pandas pyarrow      # only needed to regenerate the sample files

    $env:SIFT_API_KEY  = "your-key"
    $env:SIFT_GRPC_URL = "https://grpc-api.development.siftstack.com"
    $env:SIFT_REST_URL = "https://api.development.siftstack.com"   # import uses REST

Run:
    python import_csv_and_parquet.py
"""

import csv
import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sift_client.client import SiftClient
from sift_client.sift_types.data_import import (
    CsvDataColumn,
    CsvImportConfig,
    CsvTimeColumn,
    DataTypeKey,
    ParquetDataColumn,
    ParquetFlatDatasetImportConfig,
    ParquetTimeColumn,
    TimeFormat,
)
from sift_client.sift_types.ingestion import ChannelDataType

ASSET_NAME = os.getenv("IMPORT_ASSET_NAME", "drone-import-demo")
HERE = Path(__file__).parent
CSV_PATH = HERE / "sample_telemetry.csv"
PARQUET_PATH = HERE / "sample_telemetry.parquet"

# Flat schema: a timestamp column plus one column per channel.
CHANNELS = ["attitude.roll", "attitude.pitch", "attitude.yaw", "battery.voltage"]


def make_sample_data(rows: int = 50, hz: float = 10.0) -> None:
    """Write a small CSV and Parquet file if they do not already exist.

    Both use a flat schema (one column per channel), which is what Sift's
    Parquet import requires and what its CSV import expects.
    """
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    records = []
    for i in range(rows):
        t = start + timedelta(seconds=i / hz)
        records.append({
            "timestamp": t.isoformat(),  # RFC3339
            "attitude.roll": round(0.5 * math.sin(i / 10), 4),
            "attitude.pitch": round(0.5 * math.cos(i / 10), 4),
            "attitude.yaw": round((i / rows) * math.pi, 4),
            "battery.voltage": round(12.6 - i * 0.01, 4),
        })

    if not CSV_PATH.exists():
        with CSV_PATH.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["timestamp", *CHANNELS])
            w.writeheader()
            w.writerows(records)
        print(f"wrote {CSV_PATH.name}")

    if not PARQUET_PATH.exists():
        # pandas/pyarrow only needed here, for sample generation
        import pandas as pd
        pd.DataFrame.from_records(records).to_parquet(PARQUET_PATH, index=False)
        print(f"wrote {PARQUET_PATH.name}")


def build_csv_config() -> CsvImportConfig:
    """Explicit CSV config. Column numbers are 1-based and match the sample
    layout (timestamp first, then the channels). If an import misattributes
    columns, confirm the numbering against your file or use detect_config()."""
    return CsvImportConfig(
        asset_name=ASSET_NAME,
        run_name="csv-import-demo",
        first_data_row=2,  # header on row 1
        time_column=CsvTimeColumn(format=TimeFormat.ABSOLUTE_RFC3339, column=1),
        data_columns=[
            CsvDataColumn(name="attitude.roll", data_type=ChannelDataType.DOUBLE, units="rad", column=2),
            CsvDataColumn(name="attitude.pitch", data_type=ChannelDataType.DOUBLE, units="rad", column=3),
            CsvDataColumn(name="attitude.yaw", data_type=ChannelDataType.DOUBLE, units="rad", column=4),
            CsvDataColumn(name="battery.voltage", data_type=ChannelDataType.DOUBLE, units="V", column=5),
        ],
    )


def build_parquet_config() -> ParquetFlatDatasetImportConfig:
    """Explicit Parquet config. Parquet columns are addressed by name (path)."""
    return ParquetFlatDatasetImportConfig(
        asset_name=ASSET_NAME,
        run_name="parquet-import-demo",
        time_column=ParquetTimeColumn(format=TimeFormat.ABSOLUTE_RFC3339, path="timestamp"),
        data_columns=[
            ParquetDataColumn(name="attitude.roll", data_type=ChannelDataType.DOUBLE, units="rad", path="attitude.roll"),
            ParquetDataColumn(name="attitude.pitch", data_type=ChannelDataType.DOUBLE, units="rad", path="attitude.pitch"),
            ParquetDataColumn(name="attitude.yaw", data_type=ChannelDataType.DOUBLE, units="rad", path="attitude.yaw"),
            ParquetDataColumn(name="battery.voltage", data_type=ChannelDataType.DOUBLE, units="V", path="battery.voltage"),
        ],
    )


def main() -> None:
    api_key = os.environ["SIFT_API_KEY"]
    grpc_url = os.environ["SIFT_GRPC_URL"]
    rest_url = os.environ.get("SIFT_REST_URL")

    make_sample_data()
    client = SiftClient(api_key=api_key, grpc_url=grpc_url, rest_url=rest_url)

    # Explicit-config imports. Simpler alternative: omit config and let Sift
    # detect it, e.g. client.data_import.import_from_path(
    #     CSV_PATH, asset=ASSET_NAME, data_type=DataTypeKey.CSV,
    #     time_format=TimeFormat.ABSOLUTE_RFC3339, run_name="csv-import-demo")
    csv_job = client.data_import.import_from_path(CSV_PATH, config=build_csv_config(), show_progress=True)
    print(f"CSV import job: {csv_job}")

    parquet_job = client.data_import.import_from_path(PARQUET_PATH, config=build_parquet_config(), show_progress=True)
    print(f"Parquet import job: {parquet_job}")


if __name__ == "__main__":
    main()

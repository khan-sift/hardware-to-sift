# Hardware to Sift: Ingestion Tutorial Framework

A scaffold for a tutorial that traces telemetry from a physical sensor all the way into Sift, covering every common ingestion path. This is a framework, not the finished lessons: each section gives structure, the validated facts, and build notes.

## 0. About this document

### Purpose and audience
Teach an engineer to trace a single data point from hardware to a queryable Sift channel, and to choose the right ingestion path for a given system. Three tracks share the same spine: test engineers (file and batch), embedded and software engineers (streaming), and platform engineers (connectors and scale).

### How this was validated
Every claim below was checked through three layers, so the tutorial is not built on memory or marketing.

1. Documentation: cross-checked against Sift's official ingestion docs.
2. Live environment: reconciled against a real Sift dev environment (read-only) on 2026-06-09.
3. Empirical: a streaming smoke test built and verified against the installed SDK (sift-stack-py 0.17.0).

### Status legend
Each path and format carries a status so the tutorial does not overstate support.

- **Confirmed**: in Sift docs and observed in the live environment.
- **Doc-only**: documented by Sift, but no in-house usage was observed.
- **Not importable**: checked and found unavailable through the relevant API.
- **Unverified**: claimed in marketing only, not yet confirmed.

## 1. The end-to-end data journey (the spine)

Use this as the backbone of the tutorial. Every path is a different way to cross stage 4.

1. **Source**: sensor, DAQ, flight computer, test stand, ECU, robot.
2. **Onboard capture and encoding**: sample rates, data types, units, and the timestamp or clock source. The clock is the single most common cause of bad data downstream.
3. **Edge and transport**: local logging versus live link, buffering, loss, reconnection.
4. **Ingestion boundary into Sift**: one of the five mechanisms in Section 3.
5. **Landing in the data model**: asset, channel, flow, config, run (Section 2).
6. **Validation and storage**: schema and timestamp checks, ordering, normalization. Regardless of input format, Sift normalizes and stores telemetry internally in Parquet.
7. **Post-ingestion use**: runs, rules, annotations, reports, calculated channels (Section 9).

## 2. Sift data model primer (validated vocabulary)

Teach this once. Every path references it. Real examples below come from the live environment and make good tutorial exemplars.

- **Asset**: the hardware or system the data is attributed to. Examples: `rover_1`, `NostromoLV426`, `can_example`, `LimburgHome`.
- **Channel**: one signal, with a name, data type, optional unit, and optional component. Component shows up as dotted naming, for example `motor_a.encoder` or `mainmotor.velocity`.
- **Data types** (full set observed, not just double): double, int32, int64, uint64, enum, bit field, string, bool. The tutorial should demonstrate the variety, not only doubles.
- **Flow**: a named group of channels sent together. Channel order in the flow is a contract; values must be supplied in the same order or streaming errors occur.
- **Ingestion config (telemetry config)**: the declared schema, identified by a `client_key`. Reusing the same config and key lets Sift reuse the schema for future streams. Adding flows or channels later is backward compatible; modifying existing ones is not.
- **Run**: groups data for an asset over a time period. Optional, but heavily used in practice. Runs carry tags for grouping and link to reports.
- **Calculated channel**: a derived channel defined by an expression, for example `process_memory_bytes / pow(2, 30)`. Scope is either asset-wide or bound to a specific run. Teach that distinction explicitly.
- **Rule**: a condition over channels, for example `mainmotor.velocity > 20`, that fires actions such as a data-review annotation.

## 3. The ingestion mechanisms (the corrected core)

Sift exposes five ingestion mechanisms. Promote these to the backbone of the tutorial, and treat file formats and field protocols as a layer that rides on top of them, not as mechanisms themselves.

| Mechanism | Transport | Status | Notes |
|---|---|---|---|
| Config-based streaming | gRPC | Confirmed, primary | Define a schema, stream structured messages. Lead with this. |
| Protobuf streaming | gRPC | Confirmed, in use | Stream arbitrary protocol buffers. Real, not theoretical. |
| Data import | file or URL | Confirmed, in use | Batch upload of recorded files. See format table. |
| Schemaless JSON | REST | Doc-only | Send JSON without pre-registering a config. No in-house example found. |
| Influx line protocol | Influx client | Doc-only | Stream via any Influx client. No in-house example found. |

Client libraries (Python, Rust, Go) all wrap config-based streaming. They are a convenience layer over mechanism 1, not a separate path.

### File formats for data import
The marketing pages list more formats than the product actually imports. The live environment settles it.

| Format | Status | Evidence |
|---|---|---|
| CSV | Confirmed | Highest-volume import format in use. Requires a header row and a timestamp column. |
| Parquet | Confirmed | In use. Flat schema only: each channel is one column. |
| HDF5 | Confirmed | In use (was previously marketing-only; the live environment confirmed it). |
| TDMS | Confirmed | In use. Dedicated upload service in the SDK. |
| Chapter 10 (IRIG-106) | Confirmed | In use. Relevant to flight-test telemetry. |
| MCAP, uLog, MDF, ROS | Not importable | Absent from the live environment and not exposed as import config types. Do not claim native file import. |

### Upstream sources that ride on a mechanism
These are real data shapes but they are not standalone mechanisms. They reach Sift through one of the five above.

- **CAN / DBC**: DBC-decoded CAN frames stream in as channels (see `can_example`). Relevant if a drone uses DroneCAN / UAVCAN.
- **MQTT, PLCs**: field-bus and plant-floor sources. Bridge to streaming. Unverified as first-class connectors.
- **ROS / MCAP files**: not importable natively. Convert to CSV or Parquet, or stream live.

## 4. Choosing a path (decision framework)

| If the data is... | Use |
|---|---|
| Live and you control the schema | Config-based streaming |
| Live but already serialized as protobufs | Protobuf streaming |
| Recorded in CSV, Parquet, HDF5, TDMS, or Chapter 10 | Data import |
| Recorded in MCAP, uLog, MDF, or ROS | Convert to CSV or Parquet first, or stream live instead |
| Coming from an Influx-speaking system | Influx line protocol |
| Arriving as ad hoc JSON with no fixed schema | Schemaless JSON over REST |

Secondary factors: throughput and volume, language and runtime, edge connectivity, and how stable the schema is over time.

## 5. The SDK reality (easy to get wrong)

There are two SDK generations live in the Python package, and the public docs currently teach the older one.

- `sift_py`: what the docs teach today. Deprecated as of v0.10.0 and scheduled for removal in v1.0.0.
- `sift_client`: the forward-looking module (`SiftClient`, `SiftConnectionConfig`, resource-based API).

Guidance for the tutorial:
- Target `sift_client` for longevity. Show `sift_py` only as the currently-documented fallback.
- Pin the dependency so a fresh install does not silently break: `sift-stack-py>=0.17,<1.0` keeps `sift_py` available while remaining labs are migrated. Lab 01 already includes the `sift_client` port (`stream_attitude_sift_client.py`).
- State explicitly that Sift's published examples lag the SDK, so verify against the installed version, not the docs.

## 6. Hands-on labs (shared template)

Apply the same six steps to every lab so the muscle memory transfers across paths.

1. When to use this path and when not to.
2. Prerequisites and auth (API token plus the environment gRPC or REST URL).
3. Define the schema (config) or the file mapping.
4. The ingest action itself.
5. Verify the data landed in Sift.
6. Common failure modes.

Suggested labs, mapped to real assets:
- Lab 1, config-based streaming: model on `rover_1` or `NostromoLV426`, or run the SITL smoke test in Section 7.
- Lab 2, protobuf streaming: model on the protobuf benchmark assets.
- Lab 3, data import: CSV first, then Parquet (the two highest-volume confirmed formats).
- Lab 4, CAN / DBC: model on `can_example`.
- Lab 5, optional: schemaless JSON over REST and Influx line protocol. Flag that there is no in-house reference yet, so this lab also builds the first one.

## 7. Capstone: a real drone, end to end

A physical source validates the whole framework by construction. Sequence it so the software pipeline is proven before any money or crash risk.

### Step 0: simulation first (free)
Run PX4 or ArduPilot SITL on a laptop. It emits real MAVLink telemetry with no hardware. Point the streaming smoke test at it to prove mechanism 1 end to end before buying anything. The validated harness is `sitl_to_sift_smoketest.py` (reads MAVLink ATTITUDE, streams roll, pitch, yaw into Sift over gRPC).

### Tier A: software-only, cheapest
A DJI Tello EDU class drone. Programmable over Python, streams UDP state at roughly 10 Hz (attitude, battery, height, velocity). Exercises config-based streaming with zero soldering. Caveats: limited and derived telemetry, and uncertain US availability, so confirm stock or pick an equivalent SDK drone.

### Tier B: full-framework rig
A small ArduPilot or PX4 quad with a Pixhawk-class flight controller and a Raspberry Pi companion. One vehicle exercises two paths:
- Live MAVLink to a Python client to Sift streaming (real-time path).
- Post-flight logs for the batch path. Confirmed constraint: `.ulg` and ROS / MCAP do not import natively, so convert logs to CSV or Parquet before import.
- Add a Sift rule on a condition such as battery sag to exercise the post-ingestion layer.

### Safety and legal
Anything over 250 g requires FAA registration in the US, and you want an open area. The sub-250 g Tier A is the lowest-friction for legal test flights.

## 8. Verification, validation, and troubleshooting

Failure modes seen in the live environment, worth teaching directly:
- Timestamp parsing: unsupported integer time formats and empty timestamps are real, recurring import failures. CSV timestamp columns must match a supported format.
- Channel order in a flow: values must match the declared channel order or streaming errors occur.
- Schema and unit mismatch: do not modify existing flows or channels under a given client key; only add.
- Import job states to expect: succeeded, pending, in-progress, failed (including cancelled and retried-too-many-times).

Bake in the three-layer validation method as a reusable practice: docs, live environment, empirical. Each layer catches what the others miss. Documentation alone, for example, would have taught a deprecated SDK.

## 9. Post-ingestion (closing the loop)

Richer than a single step. Cover:
- Runs and tags for grouping (for example `simulator`, test-campaign tags).
- Reports, which auto-wire to runs via a default report ID.
- Rules that fire data-review annotations.
- Calculated channels, scoped asset-wide or per run.

## 10. Appendix

- **Auth**: every mechanism needs an API token and the correct environment URL. Never hard-code secrets; read from environment variables.
- **Streaming reference**: the validated `TelemetryConfig` to `FlowConfig` to `ChannelConfig` to `IngestionService.ingest_flows` pattern, with ordered channel values. See `sitl_to_sift_smoketest.py`.
- **Glossary**: asset, channel, component, flow, ingestion config, client key, run, calculated channel, rule.
- **Caution on the dev environment**: it is full of CI and benchmark artifacts, and object names can be misleading (an asset named for 250k channels held zero). Use the genuine assets named in Section 2 as exemplars.

## Open items

1. Empirical end-to-end run still pending: needs a connected environment plus a running SITL to land real data.
2. Done: streaming smoke test ported to `sift_client` (lab 01, `stream_attitude_sift_client.py`). Live end-to-end run still pending per item 1.
3. Build or locate a reference example for schemaless JSON over REST and for Influx line protocol.
4. Confirm whether MCAP, uLog, MDF, or ROS have any supported non-import path before mentioning them at all.

---
*Validation provenance: Sift docs, a read-only Sift dev environment, and sift-stack-py 0.17.0, as of 2026-06-09.*

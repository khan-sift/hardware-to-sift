# Capstone: a real drone, end to end

Sequenced so the software pipeline is proven before any money or crash risk.

- Step 0: PX4 or ArduPilot SITL (free). Reuse `labs/01-config-streaming/sitl_to_sift_smoketest.py`.
- Tier A: a Tello EDU class drone, software-only streaming.
- Tier B: an ArduPilot or PX4 quad with a companion computer. Live MAVLink streaming, plus a batch leg.

Confirmed constraint: `.ulg` and ROS / MCAP do not import natively. Convert post-flight logs to CSV or Parquet, or rely on live streaming.

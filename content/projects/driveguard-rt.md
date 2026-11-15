## Overview

A driving-simulation pipeline for studying how scheduling and stale observations affect control decisions. The implementation includes a reusable C++17 core, ROS 2 perception and control nodes, synthetic inputs, and a CARLA adapter.

## Architecture

Synthetic scene or CARLA RGB/depth → timestamped sensor frame → C++ perception scheduler → observation → independent control loop → brake command and CSV recording.

## Implementation

A bounded queue supports FIFO and latest-frame policies. Processing runs separately from the control loop, which checks observation age before applying time-to-collision-based decisions. The ROS 2 nodes use typed messages for frames, observations, and control commands.

The perception source includes simulator-ground-truth, depth-region, and optional OpenCV DNN / ONNX paths. The offline benchmark is a deterministic scheduling model; it does not measure GPU inference or real-vehicle performance.

## Technical Highlights

- Bounded buffering, explicit drop behavior, and timestamp propagation.
- Separation of processing throughput from control-loop freshness.
- Reproducible overload experiments comparing FIFO, latest-frame, and stale-data guards.

## Results

Local validation rebuilt the C++ core, regenerated twelve offline scenario outputs, and passed the overload regression. Two protocol tests also passed, covering CARLA depth decoding and little-endian depth serialization.

ROS 2 and CARLA integration code was reviewed; simulator and GPU integration were not run in this validation.

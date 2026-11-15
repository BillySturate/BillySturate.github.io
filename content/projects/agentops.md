## Overview

A local operations workbench for investigating and recovering a C++ HTTP service. It combines real telemetry, a read-only investigation workflow, an approval gate, and an audit trail.

## Architecture

C++ worker-pool service → Prometheus metrics and Loki logs → read-only MCP tools → LangGraph investigation → incident report → human approval → allowlisted recovery → fresh HTTP verification.

## Implementation

The C++ target exports request counters, latency histograms, queue depth, and structured logs. FastAPI serves the dashboard and incident APIs; SQLite stores incident transitions and audit events.

The investigation graph collects health, configuration, metrics, and logs. It supports deterministic diagnostic rules and optional LLM tool calling. Recovery sits outside the graph: an approval API claims a pending incident atomically, applies a fixed recovery action, and verifies the target with new requests.

## Technical Highlights

- Read-only MCP tools with an explicit fallback path for evidence collection.
- A bounded investigation workflow with optional LLM-assisted analysis.
- Compare-and-set approval state, allowlisted recovery, and persistent audit records.
- Fault-injection scenarios for latency, errors, and queue saturation.

## Validation

The C++ target compiled locally and all five diagnosis-rule tests passed. This validation did not start the Docker telemetry stack or make external model calls.

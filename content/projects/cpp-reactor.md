## Overview

A multi-reactor HTTP server with an acceptor loop, a pool of worker event loops, and per-connection read/write buffers. The repository contains both C and C++ implementations.

## Architecture

TCP acceptor → worker-loop selection → channel registration → I/O dispatcher → connection callbacks → HTTP parsing and response buffers.

## Implementation

Each event loop owns its channels and processes a task queue for registration changes. Cross-thread tasks wake the destination loop through a socket pair. A dispatcher interface provides select, poll, and Linux epoll backends; the inspected C++ constructor currently selects the select backend.

Connections combine incremental HTTP parsing, header handling, file responses, and buffered socket I/O. Worker loops are selected in round-robin order.

## Technical Highlights

- Clear separation between accepting connections and processing their events.
- Event-loop ownership and socket-pair wakeups for cross-thread changes.
- Replaceable I/O dispatchers and explicit buffer management.

## Validation

The C++ architecture was checked against the local source. An archived, resource-limited probe of the companion C implementation passed short HTTP response checks, then recorded a segmentation fault during the sixteen-worker case. That probe does not establish sustained capacity or C++ throughput; stability verification remains a prerequisite for performance claims.

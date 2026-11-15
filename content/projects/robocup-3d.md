## Overview

A multi-agent soccer team for the SimSpark / rcssserver3d environment. The local team code extends the UT Austin Villa 3D simulation base and connects world modeling, formation placement, tactical decisions, and parameterized motion skills.

## Architecture

Server percepts → world model → formation targets and role assignment → tactical behavior → motion skills → simulator commands.

## Implementation

The formation module interpolates player positions from field regions around the ball. A distance-cost matrix feeds a Hungarian assignment solver to map players to formation targets or the ball role. The behavior layer uses those assignments for positioning, collision avoidance, and kicking decisions.

Motion skills are described as sequences of joint targets and timing parameters. Simulator communication, localization, and the motion engine are integrated through the upstream base.

## Technical Highlights

- Ball-conditioned formation interpolation rather than a single fixed team shape.
- Explicit assignment between players and tactical positions.
- A common path from world-state estimates to role-specific movement and skills.

## Validation

The assignment module compiled locally and passed a known-cost matching smoke check. Full-match evaluation requires SimSpark / rcssserver3d and its native dependencies.

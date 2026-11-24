# Deadlock Win Predictor
By Taha, Jaeah, and Carter

This project builds a live-win predictor tool for Deadlock matches that estimates win probabilities as games unfold using player-level telemetry data across 180-second match intervals.  

## Overview

The Problem: Most players and analysts already recognize that a net worth lead correlates with winning. Yet, it is often unclear which concrete objectives or playstyles (such as boss damage, lane/neutral farm, denies, healing/damage mitigation, item timings, etc.) drive wins beyond soul/networth gaps. At the same time, raw Deadlock Parquet and JSON match data is large and deeply nested, making naive processing slow and error-prone. By combining resumable ingestion, cleaning, and 180-second temporal features, the project models live-win probability while surfacing high-leverage objectives and strategies over time. 

Target Audience: Deadlock players looking for data-backed objective priorities and macro/micro strategies, as well as data scientists and esports analysts building live-win probability and feature-attribution tools. 

## Getting Started
### Prerequisites

### Installation
```bash
git clone https://github.com/jaeahcodes/deadlock-win-predictor
cd deadlock-win-predictor
# Install dependencies
``` 

To extract Deadlock match metadata, clone the Github repository and run: 
```python3 scripts/data_extraction/cli.py```

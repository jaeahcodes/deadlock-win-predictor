import duckdb
import requests
from pathlib import Path
from datetime import datetime
"""
This script executes in the following order:
(1) Creates a "data" folder if it doesn't already exist, and initializes a .duckdb file.
(2) Initializes an extraction log .txt file.
(3) 
"""

# 1. Initialize paths and logging
base_dir = Path().resolve().parent
data_dir = base_dir / "data"

db_path = str(data_dir / "deadlock.duckdb")
log_path = data_dir / "extraction_logs.txt"

def log_message(message: str):
    """Prints to terminal and appends to extraction_logs.txt simultaneously."""
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S] CT")
    formatted_msg = f"---{timestamp}---\n{message}"
    print(message)

    with open(log_path, "a", encoding = "utf-8") as f:
        f.write(formatted_msg + "\n")

log_message(f"Starting Extraction Run | DB Path: {db_path}")


import argparse
import asyncio

from bin_telemetry import clean_and_bin_metadata
from common import MAX_TARGET_MATCHES
from extract_metadata import fetch_metadata_async

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog = "deadlock-cli", description = "Deadlock Telemetry CLI.")
    subparsers = parser.add_subparsers(dset = "command", required = True)

    p_extract = subparsers.add_parser("extract", help = "Fetch raw match metadata to ZSTD Parquet.")
    p_extract.add_argument("--max-matches", type = int, default = MAX_TARGET_MATCHES)
    p_extract.add_argument("--batch-size", type = int, default = 1000)
    p_extract.add_argument("--slice-start", type = int, default = 0)
    p_extract.add_argument("--slice-end", type = int, default = 30)
    p_extract.add_argument("--raw-dir", type = str, default = None)

    p_bin = subparsers.add_parser("bin", help = "Clean and bin staged metadata into timeseries Parquet.")
    p_bin.add_argument("--batch_size", type = int, default = 100)
    p_bin.add_argument("--bin-seconds", type = int, default = 180)
    p_bin.add_argument("--raw-dir", type = str, default = None)
    p_bin.add_argument("--timeseries-dir", type = str, default = None)

    p_all = subparsers.add_parser("all", help = "Run extraction followed by binning.")
    p_all.add_argument("--max_matches", type = int, default = MAX_TARGET_MATCHES)
    p_all.add_argument("--extract-batch-size", type = int, default = 1000)
    p_all.add_argument('--bin-batch-size', type = int, default = 100)
    p_all.add_argument("--bin-seconds", type = int, default = 180)
    p_all.add_argument("--slice-start", type = int, default = 0)
    p_all.add_argument("--slice-end", type = int, default = 30)
    p_all.add_argument("--raw-dir", type = str, default = None)
    p_all.add_argument("--timeseries-dir", type = str, default = None)

    return parser

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "extract":
        asyncio.run(
            fetch_metadata_async(
                max_matches = args.max_matches,
                batch_size = args.batch_size,
                slice_start = args.slice_start,
                slice_end = args.slice_end,
                raw_dir = args.raw_dir
            )
        )

    elif args.command == "bin":
        clean_and_bin_metadata(
            batch_size = args.batch_size,
            bin_seconds = args.bin_seconds,
            raw_dir = args.raw_dir,
            timeseries_dir_override = args.timeseries_dir
        )

    elif args.command == "all":
        asyncio.run(
            fetch_metadata_async(
                max_matches = args.max_matches,
                batch_size = args.extract_batch_size,
                slice_start = args.slice_start,
                slice_end = args.slice_end,
                raw_dir = args.raw_dir
            )
        )
        clean_and_bin_metadata(
            batch_size = args.bin_batch_size,
            bin_seconds = args.bin_seconds,
            raw_dir = args.raw_dir,
            timeseries_dir_override = args.timeseries_dir
        )

if __name__ == "__main__":
    main()
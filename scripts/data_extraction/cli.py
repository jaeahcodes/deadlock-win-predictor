import argparse
import asyncio
import sys

from bin_telemetry import clean_and_bin_metadata
from common import MAX_TARGET_MATCHES, log_path, resolve_dirs
from extract_metadata import fetch_metadata_async

def print_status(raw_dir: str | None = None, timeseries_dir_override: str | None = None) -> None:
    """Displays current staged and binned Parquet counts."""
    raw_path, ts_path = resolve_dirs(raw_dir = raw_dir, timeseries_dir_override = timeseries_dir_override)
    raw_count = len(list(raw_path.glob("metadata_part_*.parquet")))
    ts_count = len(list(ts_path.glob("tick_stats_part_*.parquet")))

    print("\n--- Current Pipeline Status ---")
    print(f"Raw metadata parts     : {raw_count} ({raw_path})")
    print(f"Timeseries parts       : {ts_count} ({ts_path})")
    print(f"Log file               : {log_path}")

def _prompt_int(label: str, default: int) -> int:
    raw = input(f"{label} [{default}]: ").strip()
    if not raw:
        return default
    try:
        val = int(raw)
        return val if val > 0 else default
    except ValueError:
        print(f"Invalid number '{raw}', using default ({default}).")
        return default

def _prompt_str(label: str, default: str | None) -> str | None:
    shown = default if default else "default"
    raw = input(f"{label} [{shown}]: ").strip()
    return raw if raw else default

def run_interactive_menu() -> None:
    """Interactive terminal menu when 'cli.py' is run with no arguments."""
    raw_dir: str | None = None
    ts_dir: str | None = None

    while True:
        print("\n==========================================")
        print("      DEADLOCK TELEMETRY PIPELINE CLI     ")
        print("==========================================")
        print("1. Extract Match Metadata (Async -> Parquet)")
        print("2. Clean & Bin Telemetry (Parquet -> Parquet)")
        print("3. Run Full Pipeline (Extract + Bin)")
        print("4. Check Output Status & Folders")
        print("5. Exit")

        choice = input("\nSelect an option (1-5): ").strip()

        try:
            if choice == '1':
                max_matches = _prompt_int("Max target matches", MAX_TARGET_MATCHES)
                batch_size = _prompt_int("Extract batch size", 1000)
                slice_start = _prompt_int("Manifest slice start", 0)
                slice_end = _prompt_int("Manifest slice end", 30)
                raw_dir = _prompt_str("Custon raw Parquet dir", raw_dir)

                asyncio.run(
                    fetch_metadata_async(
                        max_matches = max_matches,
                        batch_size = batch_size,
                        slice_start = slice_start,
                        slice_end = slice_end,
                        raw_dir = raw_dir
                    )
                )
                print_status(raw_dir = raw_dir, timeseries_dir_override = ts_dir)

            elif choice == '2':
                bin_seconds = _prompt_int("Time bin width in seconds (e.g. 180 or 300)", 180)
                batch_size = _prompt_int("Binning batch size", 100)
                raw_dir = _prompt_str("Custom raw Parquet dir", raw_dir)
                ts_dir = _prompt_str("Custom timeseries Parquet dir", ts_dir)

                clean_and_bin_metadata(
                    batch_size = batch_size,
                    bin_seconds = bin_seconds, 
                    raw_dir = raw_dir,
                    timeseries_dir_override = ts_dir
                )
                print_status(raw_dir = raw_dir, timeseries_dir_override = ts_dir)
            
            elif choice == "3":
                max_matches = _prompt_int("Max target matches", MAX_TARGET_MATCHES)
                ext_batch = _prompt_int("Extract batch size", 1000)
                bin_batch = _prompt_int("Binning batch size", 100)
                bin_seconds = _prompt_int("Time bin width in seconds", 180)
                raw_dir = _prompt_str("Custom raw Parquet dir", raw_dir)
                ts_dir = _prompt_str("Custom timeseries Parquet dir", ts_dir)

                asyncio.run(
                    fetch_metadata_async(
                        max_matches = max_matches,
                        batch_size = ext_batch,
                        raw_dir = raw_dir,
                    )
                )
                clean_and_bin_metadata(
                    batch_size = bin_batch,
                    bin_seconds = bin_seconds,
                    raw_dir = raw_dir,
                    timeseries_dir_override = ts_dir,
                )
                print_status(raw_dir = raw_dir, timeseries_dir_override = ts_dir)

            elif choice == '4':
                print_status(raw_dir = raw_dir, timeseries_dir_override = ts_dir)

            elif choice == '5': 
                print("Exiting. Goodbye.")
                break

            else: 
                print("Please print a number from 1 to 5.")

        except KeyboardInterrupt:
            print("\nInterrupted by user. Returning to menu...")
        except Exception as e:
            print(f"\nStep encountered an error: {e}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog = "deadlock-cli", description = "Deadlock Telemetry CLI.")
    subparsers = parser.add_subparsers(dest = "command", required = True)

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
    if len(sys.argv) == 1:
        run_interactive_menu()
        return
    
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == "status":
            print_status(raw_dir = args.raw_dir, timeseries_dir_override = args.timeseries_dir)
        
    
        elif args.command == "extract":
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

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")

if __name__ == "__main__":
    main()
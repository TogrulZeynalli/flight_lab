"""Flight Schedule Parser and Query Tool - command-line entry point.

Run from the project folder, for example:
    python flight_parser.py -i data/db.csv -a data/airports.txt
"""
import argparse
from datetime import datetime
import json
import logging
import os
import sys

from csv_loader import parse_files
from query import run_queries
from validator import load_airports

STUDENT_ID = "251ADB087"
FIRST_NAME = "Toghrul"
LAST_NAME = "Zeynalli"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="flight_parser.py",
        description="Validate flight schedule CSVs and query the flight database.",
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("-i", dest="input_file", help="Parse a single CSV file.")
    source_group.add_argument(
        "-d", dest="input_dir", help="Parse every .csv file in a folder."
    )
    source_group.add_argument(
        "-j", dest="json_db", help="Load an existing JSON database."
    )

    parser.add_argument("-a", dest="airports_file", help="Airport list file.")
    parser.add_argument(
        "-o", dest="output_db", default=None, help="Output path for JSON database."
    )
    parser.add_argument("-q", dest="query_file", help="Query JSON file.")
    parser.add_argument(
        "-r",
        dest="response_dir",
        default=".",
        help="Folder for query response file.",
    )
    return parser


def _print_error(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)


def _validate_loaded_db(data: object) -> bool:
    return isinstance(data, list) and all(isinstance(item, dict) for item in data)


def _validate_loaded_queries(data: object) -> bool:
    if isinstance(data, dict):
        return True
    if isinstance(data, list) and all(isinstance(item, dict) for item in data):
        return True
    return False


def main(argv: list[str] | None = None) -> int:
    """Run the whole program and return the exit code (0, 1 or 2).

    argv is the argument list without the program name.
    None means use sys.argv[1:] (argparse does this for you).
    Do not call sys.exit() inside main(); return the code instead.
    """
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 2
        return code

    # CLI usage checks (exit code 2)
    if args.input_file is not None or args.input_dir is not None:
        if args.airports_file is None:
            try:
                parser.error("argument -a is required when using -i or -d")
            except SystemExit:
                return 2
        if args.output_db is None:
            args.output_db = "db.json"
    else:
        # Using -j
        if args.output_db is not None:
            try:
                parser.error("argument -o is not allowed when using -j")
            except SystemExit:
                return 2

    db: list[dict] = []

    # Mode 1 & 2: CSV input (-i or -d)
    if args.input_file is not None or args.input_dir is not None:
        if not os.path.isfile(args.airports_file):
            _print_error(f"Airport file not found: {args.airports_file}")
            return 1

        try:
            airports = load_airports(args.airports_file)
        except OSError as exc:
            _print_error(f"Cannot read airport file: {exc}")
            return 1

        csv_paths: list[str] = []
        if args.input_file is not None:
            if not os.path.isfile(args.input_file):
                _print_error(f"Input CSV file not found: {args.input_file}")
                return 1
            csv_paths = [args.input_file]
        else:
            if not os.path.isdir(args.input_dir):
                _print_error(f"Input folder not found: {args.input_dir}")
                return 1
            try:
                entries = sorted(os.listdir(args.input_dir))
            except OSError as exc:
                _print_error(f"Cannot read folder: {exc}")
                return 1

            for name in entries:
                full_path = os.path.join(args.input_dir, name)
                if os.path.isfile(full_path) and name.endswith(".csv"):
                    csv_paths.append(full_path)

            if not csv_paths:
                _print_error(f"No .csv files found in folder: {args.input_dir}")
                return 1

        out_dir = os.path.dirname(os.path.abspath(args.output_db))
        log_path = os.path.join(out_dir, "errors.log")

        logger = logging.getLogger("flight_parser")
        logger.setLevel(logging.INFO)
        handler = None

        try:
            db, error_messages = parse_files(csv_paths, airports)

            handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s %(levelname)s %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            logger.addHandler(handler)

            for msg in error_messages:
                logger.warning(msg)

            with open(args.output_db, "w", encoding="utf-8") as out_f:
                json.dump(db, out_f, indent=2)

        except OSError as exc:
            _print_error(f"File I/O error: {exc}")
            return 1
        finally:
            if handler is not None:
                logger.removeHandler(handler)
                handler.close()

    # Mode 3: Existing JSON database (-j)
    else:
        if not os.path.isfile(args.json_db):
            _print_error(f"JSON database not found: {args.json_db}")
            return 1
        try:
            with open(args.json_db, "r", encoding="utf-8") as jf:
                loaded_db = json.load(jf)
        except (OSError, json.JSONDecodeError) as exc:
            _print_error(f"Invalid JSON database: {exc}")
            return 1

        if not _validate_loaded_db(loaded_db):
            _print_error("JSON database must be a JSON array of objects.")
            return 1
        db = loaded_db

    # Optional query execution (-q)
    if args.query_file is not None:
        if not os.path.isfile(args.query_file):
            _print_error(f"Query file not found: {args.query_file}")
            return 1
        if not os.path.isdir(args.response_dir):
            _print_error(f"Response folder not found: {args.response_dir}")
            return 1

        try:
            with open(args.query_file, "r", encoding="utf-8") as qf:
                loaded_queries = json.load(qf)
        except (OSError, json.JSONDecodeError) as exc:
            _print_error(f"Invalid query JSON: {exc}")
            return 1

        if not _validate_loaded_queries(loaded_queries):
            _print_error("Query file must contain a query object or array of objects.")
            return 1

        responses = run_queries(db, loaded_queries)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"response_{STUDENT_ID}_{FIRST_NAME}_{LAST_NAME}_{timestamp}.json"
        response_path = os.path.join(args.response_dir, filename)

        try:
            with open(response_path, "w", encoding="utf-8") as rf:
                json.dump(responses, rf, indent=2)
        except OSError as exc:
            _print_error(f"Failed to write query response: {exc}")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
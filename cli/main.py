import argparse
import logging
import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from core.engine import ForensicEngine
from reports import json_report, markdown_report, html_report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="forensicsuite",
        description="ForensicSuite v1.1 – modulárna analytická platforma.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Spusti analýzu projektu")
    scan_parser.add_argument("path", help="Cesta k projektu")
    scan_parser.add_argument("--config", default="", help="Cesta k config súboru")
    scan_parser.add_argument("--formats", default="json,markdown", help="Čiarkou oddelené formáty")
    scan_parser.add_argument("--output-dir", default="forensicsuite_report", help="Výstupný priečinok")
    scan_parser.add_argument("--verbose", action="store_true", help="Podrobný výstup")
    scan_parser.add_argument("--no-cache", action="store_true", help="Vypni cache")
    scan_parser.add_argument("--no-history", action="store_true", help="Vypni ukladanie histórie")

    server_parser = subparsers.add_parser("server", help="Spusti HTTP API server")
    server_parser.add_argument("--host", default="127.0.0.1", help="Host")
    server_parser.add_argument("--port", type=int, default=8765, help="Port")

    from cli.history_cmd import add_history_parser
    add_history_parser(subparsers)

    return parser


def main(argv=None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.command == "scan":
        return _run_scan(args)
    elif args.command == "server":
        return _run_server(args)
    elif hasattr(args, "func"):
        return args.func(args)

    parser.print_help()
    return 1


def _progress_callback(name: str, current: int, total: int) -> None:
    pct = int(current / total * 100)
    bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
    print(f"\r[{bar}] {pct}% – {name} ({current}/{total})", end="", flush=True)


def _run_scan(args: argparse.Namespace) -> int:
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING)

    engine = ForensicEngine(
        config_path=args.config,
        history_enabled=not args.no_history,
    )

    if not args.verbose:
        print("Analyzujem...")
        result = engine.run(args.path, progress_callback=_progress_callback)
        print()
    else:
        result = engine.run(args.path)

    os.makedirs(args.output_dir, exist_ok=True)
    formats = [f.strip() for f in args.formats.split(",") if f.strip()]

    for fmt in formats:
        if fmt == "json":
            out_path = os.path.join(args.output_dir, "report.json")
            json_report.generate(result, out_path)
            print(f"JSON report: {out_path}")
        elif fmt == "markdown":
            out_path = os.path.join(args.output_dir, "report.md")
            markdown_report.generate(result, out_path)
            print(f"Markdown report: {out_path}")
        elif fmt == "html":
            out_path = os.path.join(args.output_dir, "report.html")
            html_report.generate(result, out_path)
            print(f"HTML report: {out_path}")
        else:
            print(f"Neznámy formát: '{fmt}'", file=sys.stderr)

    scores = result.get("scores", {})
    print("\n=== Skóre ===")
    critical = False
    for name, data in scores.items():
        score = data.get("score")
        if score is not None and score < 50:
            critical = True
        print(f"{name}: {'N/A' if score is None else score}")

    if result.get("history_id"):
        print(f"\n✅ Uložené do histórie (ID: {result['history_id']})")
    elif result.get("history_error"):
        print(f"\n⚠️ Chyba pri ukladaní histórie: {result['history_error']}")

    return 2 if critical else 0


def _run_server(args: argparse.Namespace) -> int:
    from server.api import run_server
    run_server(host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())

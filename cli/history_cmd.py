import argparse

from core.history import HistoryManager


def add_history_parser(subparsers) -> None:
    parser = subparsers.add_parser("history", help="Zobraziť históriu skenov")
    parser.add_argument("--project", "-p", help="Cesta k projektu", default=None)
    parser.add_argument("--limit", "-n", type=int, default=20, help="Počet záznamov")
    parser.add_argument("--trend", "-t", choices=["maintainability", "architecture", "security"], help="Zobraziť trend")
    parser.add_argument("--stats", "-s", action="store_true", help="Zobraziť štatistiky")
    parser.set_defaults(func=run_history)


def run_history(args: argparse.Namespace) -> int:
    history = HistoryManager()

    if args.stats:
        stats = history.get_stats()
        print(f"Celkovo skenov: {stats['total_scans']}")
        print(f"Projektov: {stats['total_projects']}")
        print("Top projekty:")
        for item in stats.get("top_projects", []):
            print(f"  - {item['project']}: {item['scans']} skenov")
        return 0

    if args.trend:
        if not args.project:
            print("Chyba: pre trend je potrebné zadať --project")
            return 1
        trend = history.get_trend(args.project, args.trend)
        if not trend:
            print(f"Žiadne dáta pre projekt {args.project}")
            return 0
        print(f"Trend {args.trend} pre {args.project}:")
        for item in trend:
            print(f"  {item['datetime']}: {item['score']}")
        return 0

    history_list = history.get_history(args.project, limit=args.limit)
    if not history_list:
        print("Žiadne záznamy v histórii.")
        return 0

    for entry in history_list:
        scores = entry.get("scores", {})
        print(f"[{entry.get('datetime')}] {entry.get('project_path')}")
        print(f"  Súborov: {entry.get('file_count')}")
        print(f"  Maintainability: {scores.get('maintainability', {}).get('score', 'N/A')}")
        print(f"  Architecture: {scores.get('architecture', {}).get('score', 'N/A')}")
        print(f"  Security: {scores.get('security', {}).get('score', 'N/A')}")
        print()
    return 0

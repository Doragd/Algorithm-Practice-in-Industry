import argparse
import ast
import json
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
RESULTS_PATH = SCRIPT_DIR / "data" / "results.json"
DEFAULT_FILTERS = ["kddcup", "w.html", "lbr.html"]

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def parse_issue(issue_body):
    payload = issue_body

    for _ in range(4):
        if not isinstance(payload, str):
            break

        text = payload.strip()
        if not text:
            raise ValueError("Empty issue body")

        for loader in (json.loads, ast.literal_eval):
            try:
                payload = loader(text)
                break
            except (json.JSONDecodeError, SyntaxError, ValueError):
                continue
        else:
            escaped_text = text.replace("\\r", "").replace("\\n", "\n")
            try:
                payload = ast.literal_eval(escaped_text)
            except (SyntaxError, ValueError) as exc:
                raise ValueError("Wrong issue body format") from exc

    if not isinstance(payload, list) or len(payload) != 1:
        raise ValueError("Issue body must be a list with exactly one item")

    item = payload[0]
    if not isinstance(item, dict):
        raise ValueError("Issue item must be an object")

    required_fields = ("confs", "year", "filter")
    missing_fields = [field for field in required_fields if field not in item]
    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

    return item


def build_filters(filter_text):
    filters = DEFAULT_FILTERS.copy()
    normalized_filter = str(filter_text or "").strip()

    if normalized_filter and normalized_filter != "默认留空就行":
        filters.extend(normalized_filter.lower().split())

    return filters


def run(confs_text, start_year, filter_text="", threads=20):
    import crawler

    confs = str(confs_text).lower().split()
    if not confs:
        raise ValueError("No conferences were provided")

    crawler.run_all(
        confs=confs,
        filter_keywords=build_filters(filter_text),
        start_year=int(start_year),
        filename=str(RESULTS_PATH),
        writename=str(RESULTS_PATH),
        threads=threads,
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Update paperBotV2 conference data from a GitHub issue body."
    )
    parser.add_argument("--issue", "-i", required=True, help="GitHub issue body")
    parser.add_argument("--threads", type=int, default=20, help="Crawler concurrency")
    return parser.parse_args()


def main():
    args = parse_args()
    item = parse_issue(args.issue)
    run(
        confs_text=item["confs"],
        start_year=item["year"],
        filter_text=item.get("filter", ""),
        threads=args.threads,
    )


if __name__ == "__main__":
    main()

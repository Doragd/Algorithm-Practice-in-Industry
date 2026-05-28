import csv
import json
import os
from datetime import datetime, timezone


STATUS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "status")
RUNS_CSV = os.path.join(STATUS_DIR, "arxiv_daily_runs.csv")

CSV_FIELDS = [
    "date",
    "run_id",
    "run_attempt",
    "workflow",
    "trigger",
    "status",
    "stage",
    "started_at",
    "ended_at",
    "duration_seconds",
    "total_papers",
    "cs_ir_papers",
    "cs_cl_papers",
    "cs_cv_papers",
    "rough_rank_total",
    "rough_rank_success",
    "rough_rank_failed",
    "fine_rank_total",
    "fine_rank_success",
    "fine_rank_failed",
    "avg_rough_score",
    "avg_fine_score",
    "daily_json_written",
    "html_generated",
    "error",
]


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def today_key():
    return datetime.now().strftime("%Y%m%d")


def _duration_seconds(started_at, ended_at):
    if not started_at or not ended_at:
        return 0
    try:
        start = datetime.fromisoformat(started_at)
        end = datetime.fromisoformat(ended_at)
        return int((end - start).total_seconds())
    except ValueError:
        return 0


def _safe_avg(values):
    values = [value for value in values if isinstance(value, (int, float))]
    if not values:
        return 0
    return round(sum(values) / len(values), 2)


def _category_csv_key(category):
    return category.replace(".", "_").lower() + "_papers"


class ArxivDailyStatus:
    def __init__(self, workflow="arxiv_daily_full", trigger=None):
        self.data = {
            "date": today_key(),
            "status": "running",
            "stage": "started",
            "workflow": os.environ.get("GITHUB_WORKFLOW", workflow),
            "run_id": os.environ.get("GITHUB_RUN_ID", ""),
            "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
            "trigger": trigger or os.environ.get("GITHUB_EVENT_NAME", ""),
            "started_at": utc_now_iso(),
            "ended_at": "",
            "fetch": {
                "success": False,
                "total_papers": 0,
                "by_category": {},
            },
            "llm": {
                "rough_rank_total": 0,
                "rough_rank_success": 0,
                "rough_rank_failed": 0,
                "fine_rank_total": 0,
                "fine_rank_success": 0,
                "fine_rank_failed": 0,
                "avg_rough_score": 0,
                "avg_fine_score": 0,
            },
            "output": {
                "daily_json_written": False,
                "html_generated": False,
                "feishu_should_send": False,
            },
            "error": "",
        }

    def update_stage(self, stage):
        self.data["stage"] = stage
        self.write()

    def record_category_fetch(self, category, success, papers=0, pages=0, error=""):
        self.data["fetch"]["by_category"][category] = {
            "success": bool(success),
            "papers": int(papers or 0),
            "pages": int(pages or 0),
            "error": str(error or ""),
        }
        categories = self.data["fetch"]["by_category"].values()
        self.data["fetch"]["total_papers"] = sum(item["papers"] for item in categories)
        self.data["fetch"]["success"] = all(item["success"] for item in categories) if categories else False
        self.write()

    def record_rough_rank(self, total, success, scores):
        self.data["llm"]["rough_rank_total"] = int(total or 0)
        self.data["llm"]["rough_rank_success"] = int(success or 0)
        self.data["llm"]["rough_rank_failed"] = max(int(total or 0) - int(success or 0), 0)
        self.data["llm"]["avg_rough_score"] = _safe_avg(scores)
        self.write()

    def record_fine_rank(self, total, success, scores):
        self.data["llm"]["fine_rank_total"] = int(total or 0)
        self.data["llm"]["fine_rank_success"] = int(success or 0)
        self.data["llm"]["fine_rank_failed"] = max(int(total or 0) - int(success or 0), 0)
        self.data["llm"]["avg_fine_score"] = _safe_avg(scores)
        self.write()

    def mark_daily_json_written(self, written):
        self.data["output"]["daily_json_written"] = bool(written)
        self.write()

    def mark_html_generated(self, generated=True):
        self.data["output"]["html_generated"] = bool(generated)
        self.write()

    def mark_success(self):
        self.data["status"] = "success"
        self.data["stage"] = "completed"
        self.data["output"]["feishu_should_send"] = True
        self.data["ended_at"] = utc_now_iso()
        self.write()
        self.append_csv()

    def mark_failed(self, stage, error):
        self.data["status"] = "failed"
        self.data["stage"] = stage
        self.data["error"] = str(error)
        self.data["ended_at"] = utc_now_iso()
        self.write()
        self.append_csv()

    @property
    def json_path(self):
        return os.path.join(STATUS_DIR, f"{self.data['date']}.json")

    def write(self):
        os.makedirs(STATUS_DIR, exist_ok=True)
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def to_csv_row(self):
        by_category = self.data["fetch"]["by_category"]
        row = {
            "date": self.data["date"],
            "run_id": self.data["run_id"],
            "run_attempt": self.data["run_attempt"],
            "workflow": self.data["workflow"],
            "trigger": self.data["trigger"],
            "status": self.data["status"],
            "stage": self.data["stage"],
            "started_at": self.data["started_at"],
            "ended_at": self.data["ended_at"],
            "duration_seconds": _duration_seconds(self.data["started_at"], self.data["ended_at"]),
            "total_papers": self.data["fetch"]["total_papers"],
            "rough_rank_total": self.data["llm"]["rough_rank_total"],
            "rough_rank_success": self.data["llm"]["rough_rank_success"],
            "rough_rank_failed": self.data["llm"]["rough_rank_failed"],
            "fine_rank_total": self.data["llm"]["fine_rank_total"],
            "fine_rank_success": self.data["llm"]["fine_rank_success"],
            "fine_rank_failed": self.data["llm"]["fine_rank_failed"],
            "avg_rough_score": self.data["llm"]["avg_rough_score"],
            "avg_fine_score": self.data["llm"]["avg_fine_score"],
            "daily_json_written": str(self.data["output"]["daily_json_written"]).lower(),
            "html_generated": str(self.data["output"]["html_generated"]).lower(),
            "error": self.data["error"],
        }
        for category, category_data in by_category.items():
            key = _category_csv_key(category)
            if key in CSV_FIELDS:
                row[key] = category_data.get("papers", 0)
        return {field: row.get(field, "") for field in CSV_FIELDS}

    def append_csv(self):
        os.makedirs(STATUS_DIR, exist_ok=True)
        file_exists = os.path.exists(RUNS_CSV)
        with open(RUNS_CSV, "a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            if not file_exists:
                writer.writeheader()
            writer.writerow(self.to_csv_row())


def latest_status_for_date(date_key=None):
    date_key = date_key or today_key()
    json_path = os.path.join(STATUS_DIR, f"{date_key}.json")
    if not os.path.exists(json_path):
        return None
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def update_today_output(html_generated=None):
    date_key = today_key()
    json_path = os.path.join(STATUS_DIR, f"{date_key}.json")
    if not os.path.exists(json_path):
        return False
    with open(json_path, "r", encoding="utf-8") as f:
        status = json.load(f)
    if html_generated is not None:
        status.setdefault("output", {})["html_generated"] = bool(html_generated)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)
    _update_latest_csv_row(status)
    return True


def _update_latest_csv_row(status):
    if not os.path.exists(RUNS_CSV):
        return
    with open(RUNS_CSV, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return

    target_run_id = status.get("run_id", "")
    target_date = status.get("date", "")
    target_index = None
    for index in range(len(rows) - 1, -1, -1):
        row = rows[index]
        if target_run_id and row.get("run_id") == target_run_id:
            target_index = index
            break
        if not target_run_id and row.get("date") == target_date:
            target_index = index
            break
    if target_index is None:
        return

    output = status.get("output", {})
    rows[target_index]["html_generated"] = str(output.get("html_generated", False)).lower()
    with open(RUNS_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def needs_recovery(date_key=None):
    status = latest_status_for_date(date_key)
    if not status:
        return True, "status file missing"
    if status.get("status") != "success":
        return True, f"status is {status.get('status')}"
    output = status.get("output", {})
    if not output.get("daily_json_written"):
        return True, "daily json was not written"
    if not output.get("html_generated"):
        return True, "html was not generated"
    fetch = status.get("fetch", {})
    if not fetch.get("success"):
        return True, "fetch did not finish successfully"
    return False, "daily run already succeeded"

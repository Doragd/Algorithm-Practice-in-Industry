import os

from .status import needs_recovery, today_key


def main():
    need_recovery, reason = needs_recovery()
    print(f"recovery date: {today_key()}")
    print(f"needs_recovery: {str(need_recovery).lower()}")
    print(f"reason: {reason}")

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"needs_recovery={str(need_recovery).lower()}\n")
            f.write(f"reason={reason}\n")


if __name__ == "__main__":
    main()

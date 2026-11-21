"""Run a label-blind eval over an explicit issue set (re-run / expansion).

Usage:
  run_eval_set.py --numbers 780,779,778,777,774,773,770,769,767,766,759,757,754
  run_eval_set.py --next-below 754 --limit 10

--numbers: fetch exactly those issues (get_issue each) and score all of
  them. Used for the re-run over the same set as a previous eval file.
--next-below N: list issues newest-first, take candidates with number < N
  (non-PRs), and let run_eval take the first --limit with unambiguous
  ground truth — the mechanical continuation of the previous scan.
  Selection rule (documented, no cherry-picking): same newest-first
  order as the CLI eval, continuing below the previous set's minimum
  number; unlabelled/ambiguous issues are skipped by run_eval and
  counted, not hand-picked. --page P scans page P of the issues list
  (page 1 = newest 100); use it when the current page's candidates
  below N are exhausted.

Saves eval/results-<stamp>.json via save_eval_result and prints metrics.
One model call per issue, paced >=45 s — allow ~2 min per issue.
"""
from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, "src")

from issue_triage.cli import _setup
from issue_triage.eval import run_eval, save_eval_result
from issue_triage.triage import TriageEngine


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default="openminion/openminion")
    parser.add_argument("--numbers", default="",
                        help="comma-separated issue numbers to score exactly")
    parser.add_argument("--next-below", type=int, default=None,
                        help="continue the newest-first scan below this number")
    parser.add_argument("--limit", type=int, default=10,
                        help="issues to score (next-below mode)")
    parser.add_argument("--page", type=int, default=1,
                        help="issues-list page to scan (next-below mode; "
                        "page 1 is the newest 100)")
    args = parser.parse_args()
    if bool(args.numbers) == (args.next_below is not None):
        parser.error("pass exactly one of --numbers / --next-below")

    llm, gh, memory = _setup(None)
    engine = TriageEngine(llm=llm, github=gh, memory=memory)
    try:
        if args.numbers:
            numbers = [int(n) for n in args.numbers.split(",") if n.strip()]
            issues = [gh.get_issue(args.repo, n) for n in numbers]
            print(f"re-run over explicit set: {numbers}", flush=True)
            result = run_eval(engine, args.repo, len(numbers), issues=issues, blind=True)
        else:
            raw = gh.list_issues(args.repo, state="all", per_page=100, page=args.page)
            issues = [i for i in raw
                      if "pull_request" not in i and i["number"] < args.next_below]
            print(f"next-below {args.next_below}: {len(issues)} candidates, "
                  f"limit {args.limit}", flush=True)
            result = run_eval(engine, args.repo, args.limit, issues=issues, blind=True)
        path = save_eval_result(result)
        print(json.dumps(result["metrics"], indent=2), flush=True)
        print(f"skipped (unlabelled/ambiguous): "
              f"{result['skipped_unlabelled_or_ambiguous']}", flush=True)
        if result.get("errors"):
            print(f"errors: {len(result['errors'])}", flush=True)
            for err in result["errors"]:
                print(f"  #{err['issue_number']}: {err['error']}", flush=True)
        print(f"saved {path}", flush=True)
    finally:
        llm.close()
        gh.close()


if __name__ == "__main__":
    main()

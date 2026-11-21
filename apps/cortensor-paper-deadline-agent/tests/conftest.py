"""Shared fixtures: tiny deterministic CSVs (not the real 1000+ row tables)."""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import pytest

TODAY = date(2026, 11, 17)

CONF_HEADER = [
    "abbreviation", "full_name", "ccf_grade", "field", "abstract_deadline",
    "full_deadline", "deadline_timezone", "rebuttal", "notification",
    "camera_ready", "conf_dates", "conf_location", "website", "status",
    "source_url", "verified_date",
]
CONF_ROWS = [
    # future full, two tracks
    ["CVPR", "IEEE Conference on Computer Vision and Pattern Recognition", "A",
     "计算机视觉", "2026-11-20", "2026-11-27 (Long); 2026-12-05 (Short)", "AoE",
     "", "", "", "", "", "https://cvpr.example", "verified", "https://cvpr.example/cfp", "2026-11-16"],
    # past full, future abstract only
    ["FAKE", "Fake Abstract Only Conf", "B", "人工智能", "2026-12-01", "2026-01-15", "AoE",
     "", "", "", "", "", "https://fake.example", "verified", "https://fake.example", "2026-11-16"],
    # no future date at all -> date_unclear
    ["OLD", "Old Conf", "C", "人工智能", "", "2026-05-01", "AoE",
     "", "", "", "", "", "https://old.example", "cycle_not_announced", "https://old.example", "2026-11-16"],
    # unverified future date (cycle_not_announced keeps its last-cycle date)
    ["NEXT", "Next Cycle Conf", "A", "机器学习", "", "2027-01-15", "AoE",
     "", "", "", "", "", "https://next.example", "cycle_not_announced", "https://next.example", "2026-11-16"],
    # English month format, future
    ["ENG", "English Date Conf", "B", "数据挖掘", "", "Dec 8, 2026 (AoE, firm)", "AoE",
     "", "", "", "", "", "https://eng.example", "verified", "https://eng.example", "2026-11-16"],
    # TBD only -> date_unclear
    ["TBDX", "TBD Conf", "B", "安全", "", "TBD", "AoE",
     "", "", "", "", "", "https://tbdx.example", "verified", "https://tbdx.example", "2026-11-16"],
]

JOURNAL_HEADER = [
    "abbreviation", "full_name", "type", "field", "ccf_grade",
    "submission_method", "cycle", "fixed_deadline", "website", "status",
    "source_url", "verified_date",
]
JOURNAL_ROWS = [
    ["JTEST", "Journal of Testing", "journal", "人工智能", "A",
     "rolling", "rolling", "2026-11-30; 2026-12-30", "https://jtest.example",
     "verified", "https://jtest.example/cfp", "2026-11-16"],
    ["JROLL", "Rolling Journal", "journal", "人工智能", "B",
     "rolling", "rolling", "", "https://jroll.example",
     "verified", "https://jroll.example", "2026-11-16"],
]

LAW_HEADER = JOURNAL_HEADER + ["dblp_slug"]
LAW_ROWS = [
    ["LTEST", "Law & Tech Review", "journal", "法律", "C",
     "rolling", "rolling", "2026-12-15", "https://ltest.example",
     "verified", "https://ltest.example", "2026-11-16", "ltest"],
]

CCF_HEADER = ["abbreviation", "full_name", "type", "field", "grade", "publisher",
              "dblp_url", "change_vs_2022", "feishu_grade", "feishu_source", "notes"]
CCF_ROWS = [
    ["CVPR", "IEEE Conference on Computer Vision and Pattern Recognition",
     "conference", "计算机视觉", "A", "IEEE", "https://dblp.example/cvpr", "", "", "", ""],
]


def _write_csv(path: Path, header, rows) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


@pytest.fixture()
def data_dir(tmp_path: Path) -> Path:
    _write_csv(tmp_path / "deadlines-all-conferences.csv", CONF_HEADER, CONF_ROWS)
    _write_csv(tmp_path / "journals-submission.csv", JOURNAL_HEADER, JOURNAL_ROWS)
    _write_csv(tmp_path / "law-submission.csv", LAW_HEADER, LAW_ROWS)
    _write_csv(tmp_path / "ccf2026-full.csv", CCF_HEADER, CCF_ROWS)
    return tmp_path


@pytest.fixture()
def store(data_dir: Path):
    from paper_watch.store import VenueStore

    return VenueStore.load(data_dir, today=TODAY)

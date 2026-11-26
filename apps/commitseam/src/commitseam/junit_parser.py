from __future__ import annotations

import hashlib
import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FailureItem:
    item_id: str
    test_name: str
    classname: str
    failure_kind: str
    message: str
    payload_digest: str


def _build_digest(
    *,
    item_id: str,
    classname: str,
    test_name: str,
    failure_kind: str,
    message: str,
) -> str:
    canonical = json.dumps(
        {
            "item_id": item_id,
            "classname": classname,
            "test_name": test_name,
            "failure_kind": failure_kind,
            "message": message,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def parse_junit_failures(xml_source: str | Path) -> list[FailureItem]:
    """Deterministically extract failing/error JUnit testcases sorted by item_id."""
    if isinstance(xml_source, Path):
        raw_xml = xml_source.read_text(encoding="utf-8")
    else:
        stripped = xml_source.lstrip()
        if stripped.startswith("<"):
            raw_xml = xml_source
        else:
            raw_xml = Path(xml_source).read_text(encoding="utf-8")

    root = ET.fromstring(raw_xml)
    if root.tag == "testsuite":
        suites = [root]
    elif root.tag == "testsuites":
        suites = list(root.findall(".//testsuite"))
    else:
        raise ValueError(f"Unsupported JUnit root element: <{root.tag}>")

    items_by_id: dict[str, FailureItem] = {}
    for suite in suites:
        suite_name = (suite.attrib.get("name") or "suite").strip()
        for case in suite.findall("testcase"):
            failure_el = case.find("failure")
            error_el = case.find("error")
            chosen = failure_el if failure_el is not None else error_el
            if chosen is None:
                continue

            failure_kind = "failure" if failure_el is not None else "error"
            classname = (case.attrib.get("classname") or suite_name).strip()
            test_name = (case.attrib.get("name") or "").strip()
            if not test_name:
                continue

            item_id = f"{classname}::{test_name}" if classname else test_name
            msg_attr = (chosen.attrib.get("message") or "").strip()
            body_text = (chosen.text or "").strip()
            message = msg_attr or body_text or failure_kind
            digest = _build_digest(
                item_id=item_id,
                classname=classname,
                test_name=test_name,
                failure_kind=failure_kind,
                message=message,
            )
            candidate = FailureItem(
                item_id=item_id,
                test_name=test_name,
                classname=classname,
                failure_kind=failure_kind,
                message=message,
                payload_digest=digest,
            )
            existing = items_by_id.get(item_id)
            if existing is None or (
                candidate.failure_kind,
                candidate.message,
                candidate.payload_digest,
            ) < (
                existing.failure_kind,
                existing.message,
                existing.payload_digest,
            ):
                items_by_id[item_id] = candidate

    return [items_by_id[k] for k in sorted(items_by_id)]

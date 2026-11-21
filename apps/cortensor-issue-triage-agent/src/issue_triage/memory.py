"""Per-repo memory: past triage decisions in local JSON.

Purpose: label consistency inside one repo — before classifying a new
issue, look up what the same component / type was decided before and hand
those decisions to the classifier as reference.

Storage: ``state/<owner>__<repo>.json`` (gitignored). Export uses the SDK's
``MemoryBundle`` (export/save/load round-trip verified in SPIKE.md §2.6).
Note the SDK's public ``import_bundle()`` only validates the trust mode
and returns a summary dict — it writes nothing into any store. Our
``import_bundle_file`` does the actual load into this store; see
docs/WHAT_WE_LEARNED.md.
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import TriageDecision


class RepoMemory:
    def __init__(self, root: str | Path = "state"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _filename(repo: str) -> str:
        return repo.replace("/", "__") + ".json"

    def path_for(self, repo: str) -> Path:
        return self.root / self._filename(repo)

    def load(self, repo: str) -> list[TriageDecision]:
        path = self.path_for(repo)
        if not path.is_file():
            return []
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return []
        decisions: list[TriageDecision] = []
        for item in raw if isinstance(raw, list) else []:
            try:
                decisions.append(TriageDecision.model_validate(item))
            except Exception:
                continue
        return decisions

    def _save(self, repo: str, decisions: list[TriageDecision]) -> None:
        path = self.path_for(repo)
        path.write_text(
            json.dumps([d.model_dump() for d in decisions], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def record(self, decision: TriageDecision) -> None:
        decisions = self.load(decision.repo)
        decisions = [d for d in decisions if d.issue_number != decision.issue_number]
        decisions.append(decision)
        self._save(decision.repo, decisions)

    def mark_decided(self, repo: str, issue_number: int) -> None:
        decisions = self.load(repo)
        changed = False
        for d in decisions:
            if d.issue_number == issue_number and d.status != "decided":
                d.status = "decided"
                changed = True
        if changed:
            self._save(repo, decisions)

    def lookup(
        self, repo: str, component: str | None = None, issue_type: str | None = None, limit: int = 5
    ) -> list[TriageDecision]:
        """Past *decided* decisions first, most recent last; fall back to
        proposed ones only if nothing decided matches."""
        decisions = self.load(repo)
        decided = [d for d in decisions if d.status == "decided"]
        pool = decided or decisions
        if component:
            same = [d for d in pool if d.component == component]
            if same:
                pool = same
        if issue_type:
            same = [d for d in pool if d.issue_type == issue_type]
            if same:
                pool = same
        return list(reversed(pool))[:limit]

    def label_counts(self, repo: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for d in self.load(repo):
            for label in d.labels:
                counts[label] = counts.get(label, 0) + 1
        return counts

    # -- MemoryBundle export / import (SDK round-trip) ------------------
    def export_bundle(self, repo: str, path: str | Path) -> dict:
        from openminion.modules.memory.portability import export_bundle, save_bundle

        decisions = self.load(repo)
        bundle = export_bundle(
            [d.model_dump(mode="json") for d in decisions],
            metadata={"agent": "issue-triage", "repo": repo, "kind": "triage-decisions"},
        )
        save_bundle(bundle, path)
        return {"path": str(path), "item_count": len(decisions), "version": bundle.version}

    def import_bundle_file(self, path: str | Path, repo: str) -> int:
        """Actually load a bundle file into this store.

        The SDK's public ``import_bundle()`` returns only a summary dict
        and persists nothing; this method is the missing half.
        """
        from openminion.modules.memory.portability import import_bundle, load_bundle

        bundle = load_bundle(path)
        info = import_bundle(bundle, trust_mode="direct")
        if info.get("item_count", 0) != len(bundle.items):
            raise ValueError("bundle item count mismatch")
        decisions = self.load(repo)
        seen = {d.issue_number for d in decisions}
        added = 0
        for item in bundle.items:
            try:
                decision = TriageDecision.model_validate(item)
            except Exception:
                continue
            if decision.issue_number in seen:
                continue
            decisions.append(decision)
            seen.add(decision.issue_number)
            added += 1
        self._save(repo, decisions)
        return added

"""ReleaseGuard Minion — inspectable release-readiness auditor on OpenMinion 0.1."""

from .agent import ReleaseGuardMinion
from .models import (
    ApprovalDecisionRecord,
    AuditRunEnvelope,
    ReleaseAuditReport,
    ReleaseCheck,
)
from .policy import ReleaseApprovalGate
from .tools import (
    create_release_tag,
    inspect_ci_and_tests,
    inspect_repo_manifest,
    scan_secret_hygiene,
    write_release_brief,
)

__all__ = [
    "ApprovalDecisionRecord",
    "AuditRunEnvelope",
    "ReleaseApprovalGate",
    "ReleaseAuditReport",
    "ReleaseCheck",
    "ReleaseGuardMinion",
    "create_release_tag",
    "inspect_ci_and_tests",
    "inspect_repo_manifest",
    "scan_secret_hygiene",
    "write_release_brief",
]

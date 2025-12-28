"""
Xea Governance Oracle - Rubrics & DAO Module

Handles DAO registration and PoUW rubric management.
Rubrics are versioned and immutable once used in evidence.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from app.config import settings
from app.schemas import (
    DAO,
    DAORegisterRequest,
    Rubric,
    RubricCreateRequest,
    RubricWeights,
    ProposalTypePreset,
)


# ============================================================================
# Storage Directories
# ============================================================================

def get_daos_dir() -> Path:
    """Get the DAOs data directory."""
    daos_dir = Path(settings.data_dir) / "daos"
    if not daos_dir.exists():
        daos_dir = Path(__file__).parent.parent.parent / "data" / "daos"
    daos_dir.mkdir(parents=True, exist_ok=True)
    return daos_dir


def get_rubrics_dir() -> Path:
    """Get the rubrics data directory."""
    rubrics_dir = Path(settings.data_dir) / "rubrics"
    if not rubrics_dir.exists():
        rubrics_dir = Path(__file__).parent.parent.parent / "data" / "rubrics"
    rubrics_dir.mkdir(parents=True, exist_ok=True)
    return rubrics_dir


# ============================================================================
# DAO Management
# ============================================================================

def register_dao(request: DAORegisterRequest) -> DAO:
    """
    Register a new DAO.
    
    Args:
        request: DAO registration details
        
    Returns:
        Created DAO object
        
    Raises:
        ValueError: If DAO already exists
    """
    dao_file = get_daos_dir() / f"{request.dao_id}.json"
    
    if dao_file.exists():
        raise ValueError(f"DAO {request.dao_id} already exists")
    
    dao = DAO(
        dao_id=request.dao_id,
        name=request.name,
        description=request.description,
        default_rubric_id=request.default_rubric_id,
        created_at=datetime.now(timezone.utc),
    )
    
    with open(dao_file, "w") as f:
        json.dump(dao.model_dump(), f, indent=2, default=str)
    
    return dao


def get_dao(dao_id: str) -> Optional[DAO]:
    """Get a DAO by ID."""
    dao_file = get_daos_dir() / f"{dao_id}.json"
    
    if not dao_file.exists():
        return None
    
    with open(dao_file, "r") as f:
        data = json.load(f)
    
    return DAO(**data)


def update_dao_default_rubric(dao_id: str, rubric_id: str) -> DAO:
    """Set the default rubric for a DAO."""
    dao = get_dao(dao_id)
    if not dao:
        raise ValueError(f"DAO {dao_id} not found")
    
    dao.default_rubric_id = rubric_id
    
    dao_file = get_daos_dir() / f"{dao_id}.json"
    with open(dao_file, "w") as f:
        json.dump(dao.model_dump(), f, indent=2, default=str)
    
    return dao


def list_daos() -> List[DAO]:
    """List all registered DAOs."""
    daos = []
    for dao_file in get_daos_dir().glob("*.json"):
        with open(dao_file, "r") as f:
            data = json.load(f)
        daos.append(DAO(**data))
    return daos


# ============================================================================
# Rubric Management
# ============================================================================

def generate_rubric_id() -> str:
    """Generate a unique rubric ID."""
    return f"rubric_{uuid.uuid4().hex[:12]}"


def _rubric_filename(rubric_id: str, version: int) -> str:
    """Get filename for a rubric version."""
    return f"{rubric_id}_v{version}.json"


def create_rubric(request: RubricCreateRequest) -> Rubric:
    """
    Create a new rubric for a DAO.
    
    Args:
        request: Rubric creation details
        
    Returns:
        Created Rubric object
    """
    # Verify DAO exists
    dao = get_dao(request.dao_id)
    if not dao:
        raise ValueError(f"DAO {request.dao_id} not found")
    
    rubric_id = generate_rubric_id()
    version = 1
    
    rubric = Rubric(
        rubric_id=rubric_id,
        version=version,
        dao_id=request.dao_id,
        name=request.name,
        description=request.description,
        weights=request.weights,
        presets=request.presets,
        created_at=datetime.now(timezone.utc),
        is_immutable=False,
    )
    
    rubric_file = get_rubrics_dir() / _rubric_filename(rubric_id, version)
    with open(rubric_file, "w") as f:
        json.dump(rubric.model_dump(), f, indent=2, default=str)
    
    return rubric


def get_rubric(rubric_id: str, version: Optional[int] = None) -> Optional[Rubric]:
    """
    Get a rubric by ID and optional version.
    
    Args:
        rubric_id: Rubric identifier
        version: Specific version, or None for latest
        
    Returns:
        Rubric object or None if not found
    """
    rubrics_dir = get_rubrics_dir()
    
    if version:
        rubric_file = rubrics_dir / _rubric_filename(rubric_id, version)
        if not rubric_file.exists():
            return None
        with open(rubric_file, "r") as f:
            data = json.load(f)
        return Rubric(**data)
    
    # Find latest version
    latest_version = 0
    latest_file = None
    
    for f in rubrics_dir.glob(f"{rubric_id}_v*.json"):
        try:
            v = int(f.stem.split("_v")[-1])
            if v > latest_version:
                latest_version = v
                latest_file = f
        except ValueError:
            continue
    
    if not latest_file:
        return None
    
    with open(latest_file, "r") as f:
        data = json.load(f)
    
    return Rubric(**data)


def list_rubrics(dao_id: str) -> List[Rubric]:
    """List all rubrics for a DAO."""
    rubrics = []
    seen_ids = set()
    
    for rubric_file in get_rubrics_dir().glob("*.json"):
        with open(rubric_file, "r") as f:
            data = json.load(f)
        
        if data.get("dao_id") == dao_id:
            rid = data["rubric_id"]
            # Only return latest version of each rubric
            if rid not in seen_ids:
                rubric = get_rubric(rid)  # Gets latest version
                if rubric:
                    rubrics.append(rubric)
                    seen_ids.add(rid)
    
    return rubrics


def mark_rubric_used(rubric_id: str, version: int) -> None:
    """
    Mark a rubric version as immutable (used in evidence).
    
    Once marked, this version cannot be modified.
    """
    rubric = get_rubric(rubric_id, version)
    if not rubric:
        raise ValueError(f"Rubric {rubric_id} v{version} not found")
    
    if rubric.is_immutable:
        return  # Already immutable
    
    rubric.is_immutable = True
    
    rubric_file = get_rubrics_dir() / _rubric_filename(rubric_id, version)
    with open(rubric_file, "w") as f:
        json.dump(rubric.model_dump(), f, indent=2, default=str)


def create_rubric_version(rubric_id: str, updates: Dict) -> Rubric:
    """
    Create a new version of an existing rubric.
    
    Args:
        rubric_id: Existing rubric ID
        updates: Fields to update
        
    Returns:
        New Rubric version
    """
    current = get_rubric(rubric_id)
    if not current:
        raise ValueError(f"Rubric {rubric_id} not found")
    
    new_version = current.version + 1
    
    new_rubric = Rubric(
        rubric_id=rubric_id,
        version=new_version,
        dao_id=current.dao_id,
        name=updates.get("name", current.name),
        description=updates.get("description", current.description),
        weights=updates.get("weights", current.weights),
        presets=updates.get("presets", current.presets),
        created_at=datetime.now(timezone.utc),
        is_immutable=False,
    )
    
    rubric_file = get_rubrics_dir() / _rubric_filename(rubric_id, new_version)
    with open(rubric_file, "w") as f:
        json.dump(new_rubric.model_dump(), f, indent=2, default=str)
    
    return new_rubric


# ============================================================================
# Default Rubric
# ============================================================================

DEFAULT_RUBRIC_WEIGHTS = RubricWeights(
    accuracy=0.4,
    omission_risk=0.3,
    evidence_quality=0.2,
    governance_relevance=0.1,
)


def get_default_weights() -> RubricWeights:
    """Get default PoUW weights when no rubric is specified."""
    return DEFAULT_RUBRIC_WEIGHTS

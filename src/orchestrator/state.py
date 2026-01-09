"""
State System - Specification, Manifest, Activity History

Simplified and adapted from solution-engine.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class Specification:
    """
    User's goal/requirements (adapted from solution-engine covenant).
    
    Simplified specification system - single source of truth for what needs to be built.
    """

    service: str
    purpose: str
    maturity: Optional[str] = None
    dependencies: Optional[Dict[str, Any]] = None
    stages: Optional[Dict[str, Any]] = None
    quality_gates: Optional[Dict[str, Any]] = None
    deployment: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "service": self.service,
            "purpose": self.purpose,
            "maturity": self.maturity,
            "dependencies": self.dependencies,
            "stages": self.stages,
            "quality_gates": self.quality_gates,
            "deployment": self.deployment,
            **self.metadata,
        }

    def save(self, path: Path):
        """Save specification to YAML file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)

    @classmethod
    def load(cls, path: Path) -> "Specification":
        """Load specification from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)


@dataclass
class Manifest:
    """
    Activity execution results (simplified, activity-specific).
    
    Records what an activity ACTUALLY did:
    - Outputs created
    - Status, timestamps
    - Quality gates
    - Complete audit trail
    """

    activity: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration: Optional[str] = None
    status: str = "pending"  # pending, in_progress, complete, failed
    outputs: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    quality_gates_passed: Dict[str, bool] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def start(self):
        """Mark activity as started."""
        self.started_at = datetime.utcnow().isoformat() + "Z"
        self.status = "in_progress"

    def complete(self, success: bool = True):
        """Mark activity as completed."""
        self.completed_at = datetime.utcnow().isoformat() + "Z"
        self.status = "complete" if success else "failed"

        # Calculate duration
        if self.started_at and self.completed_at:
            start = datetime.fromisoformat(self.started_at.replace("Z", "+00:00"))
            end = datetime.fromisoformat(self.completed_at.replace("Z", "+00:00"))
            duration_seconds = (end - start).total_seconds()

            minutes = int(duration_seconds // 60)
            seconds = int(duration_seconds % 60)
            self.duration = f"{minutes}m {seconds}s"

    def add_output(self, name: str, value: Any):
        """Record an output that was created."""
        self.outputs[name] = value

    def add_error(self, error: str):
        """Record an error."""
        self.errors.append(error)
        self.status = "failed"
    
    def record_quality_gate(self, gate_name: str, passed: bool):
        """
        Record quality gate result.
        
        Args:
            gate_name: Quality gate name
            passed: Whether the gate passed
        """
        if not hasattr(self, "quality_gates_passed"):
            self.quality_gates_passed = {}
        self.quality_gates_passed[gate_name] = passed

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "activity": self.activity,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration": self.duration,
            "status": self.status,
            "outputs": self.outputs,
            "errors": self.errors,
            "quality_gates_passed": self.quality_gates_passed,
            **self.metadata,
        }

    def save(self, path: Path):
        """Save manifest to YAML file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)

    @classmethod
    def load(cls, path: Path) -> "Manifest":
        """Load manifest from YAML file."""
        if not path.exists():
            return cls(activity=path.stem.replace("-manifest", ""))
        
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        
        # Ensure quality_gates_passed exists (for backwards compatibility)
        if "quality_gates_passed" not in data:
            data["quality_gates_passed"] = {}
        
        return cls(**data)


@dataclass
class ActivityHistoryEntry:
    """Single history entry for an activity execution."""

    timestamp: str
    decision: Dict[str, Any]
    context: Dict[str, Any]
    outcome: str  # success, failure
    result: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActivityHistory:
    """
    Historical record of past decisions/outcomes for self-learning.
    
    Each activity maintains history of past executions.
    Used as context for future decisions (LLM learns from past).
    """

    activity: str
    entries: List[ActivityHistoryEntry] = field(default_factory=list)

    def add_entry(
        self,
        decision: Dict[str, Any],
        context: Dict[str, Any],
        outcome: str,
        result: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Add a history entry."""
        entry = ActivityHistoryEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            decision=decision,
            context=context,
            outcome=outcome,
            result=result,
            metadata=metadata or {},
        )
        self.entries.append(entry)

    def get_recent(self, limit: int = 10) -> List[ActivityHistoryEntry]:
        """Get recent history entries."""
        return self.entries[-limit:]

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "activity": self.activity,
            "entries": [
                {
                    "timestamp": entry.timestamp,
                    "decision": entry.decision,
                    "context": entry.context,
                    "outcome": entry.outcome,
                    "result": entry.result,
                    **entry.metadata,
                }
                for entry in self.entries
            ],
        }

    def save(self, path: Path):
        """Save history to YAML file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)

    @classmethod
    def load(cls, path: Path) -> "ActivityHistory":
        """Load history from YAML file."""
        if not path.exists():
            return cls(activity=path.stem.replace("-history", ""))
        
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        
        activity = data.get("activity", path.stem.replace("-history", ""))
        entries_data = data.get("entries", [])
        
        entries = [
            ActivityHistoryEntry(
                timestamp=entry_data["timestamp"],
                decision=entry_data["decision"],
                context=entry_data["context"],
                outcome=entry_data["outcome"],
                result=entry_data["result"],
                metadata={k: v for k, v in entry_data.items() if k not in ["timestamp", "decision", "context", "outcome", "result"]},
            )
            for entry_data in entries_data
        ]
        
        return cls(activity=activity, entries=entries)


"""
Playbook Registry - Registry-driven playbook discovery and execution

SPECTRA-Grade: Single source of truth is operations/playbooks/playbooks-registry.yaml
"""

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class Playbook:
    """Playbook definition from registry."""

    name: str
    description: str
    path: str
    activity: str  # Which activities can use this
    inputs: Optional[List[Dict[str, str]]] = None
    outputs: Optional[List[Dict[str, str]]] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize metadata if not provided."""
        if self.metadata is None:
            self.metadata = {}


class PlaybookRegistry:
    """
    Registry-driven playbook discovery and execution.
    
    SPECTRA-Grade:
    - Single source of truth: operations/playbooks/playbooks-registry.yaml
    - Registry-driven discovery (not file system scanning)
    - Version-controlled registry changes (reversible)
    """

    def __init__(self, workspace_root: Optional[Path] = None):
        """
        Initialize playbook registry.
        
        Args:
            workspace_root: SPECTRA workspace root directory. If None, auto-detects.
        """
        if workspace_root is None:
            # Find workspace root (similar to ContextBuilder)
            current = Path.cwd()
            for check_path in [current] + list(current.parents):
                if (check_path / ".spectra").exists():
                    workspace_root = check_path
                    break
                if check_path.name == "Core":
                    workspace_root = check_path.parent
                    break
        
        self.workspace_root = workspace_root
        self.registry_path = workspace_root / "Core" / "operations" / "playbooks" / "playbooks-registry.yaml"
        self._registry: Optional[Dict] = None

    def load_registry(self) -> Dict:
        """
        Load playbook registry from YAML file.
        
        Returns:
            Registry dictionary
            
        Raises:
            FileNotFoundError: If registry file does not exist
        """
        if self._registry is not None:
            return self._registry

        if not self.registry_path.exists():
            logger.warning(f"Playbook registry not found at: {self.registry_path}")
            logger.warning("Creating empty registry")
            self._registry = {"playbooks": []}
            return self._registry

        with open(self.registry_path) as f:
            self._registry = yaml.safe_load(f) or {"playbooks": []}

        logger.debug(f"Loaded playbook registry from: {self.registry_path}")
        logger.debug(f"Found {len(self._registry.get('playbooks', []))} playbooks")
        return self._registry

    def discover_playbooks(self, activity_name: str) -> List[Playbook]:
        """
        Discover playbooks for an activity.
        
        Args:
            activity_name: Activity name (e.g., "discover")
            
        Returns:
            List of Playbook objects
        """
        registry = self.load_registry()
        playbooks_data = registry.get("playbooks", [])
        
        # Filter playbooks by activity
        matching_playbooks = [
            pb for pb in playbooks_data if pb.get("activity") == activity_name
        ]
        
        playbooks = [
            Playbook(
                name=pb["name"],
                description=pb.get("description", ""),
                path=pb["path"],
                activity=pb["activity"],
                inputs=pb.get("inputs"),
                outputs=pb.get("outputs"),
                metadata={k: v for k, v in pb.items() if k not in ["name", "description", "path", "activity", "inputs", "outputs"]},
            )
            for pb in matching_playbooks
        ]
        
        logger.debug(f"Discovered {len(playbooks)} playbooks for activity: {activity_name}")
        return playbooks

    def get_playbook(self, name: str) -> Optional[Playbook]:
        """
        Get a specific playbook by name.
        
        Args:
            name: Playbook name
            
        Returns:
            Playbook object, or None if not found
        """
        registry = self.load_registry()
        playbooks_data = registry.get("playbooks", [])
        
        for pb_data in playbooks_data:
            if pb_data["name"] == name:
                return Playbook(
                    name=pb_data["name"],
                    description=pb_data.get("description", ""),
                    path=pb_data["path"],
                    activity=pb_data["activity"],
                    inputs=pb_data.get("inputs"),
                    outputs=pb_data.get("outputs"),
                    metadata={k: v for k, v in pb_data.items() if k not in ["name", "description", "path", "activity", "inputs", "outputs"]},
                )
        
        return None

    def execute_playbook(self, playbook: Playbook, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a playbook.
        
        Args:
            playbook: Playbook object
            args: Arguments to pass to playbook
            
        Returns:
            Execution result dictionary
            
        Raises:
            FileNotFoundError: If playbook file does not exist
            subprocess.CalledProcessError: If playbook execution fails
        """
        playbook_path = self.workspace_root / playbook.path
        
        if not playbook_path.exists():
            raise FileNotFoundError(f"Playbook not found: {playbook_path}")

        logger.info(f"Executing playbook: {playbook.name} ({playbook_path})")

        # Determine execution method based on file extension
        if playbook_path.suffix == ".py":
            # Python script
            result = subprocess.run(
                ["python", str(playbook_path)] + (list(args.values()) if args else []),
                capture_output=True,
                text=True,
                cwd=self.workspace_root,
            )
        elif playbook_path.suffix == ".ps1":
            # PowerShell script
            result = subprocess.run(
                ["pwsh", "-File", str(playbook_path)] + (list(args.values()) if args else []),
                capture_output=True,
                text=True,
                cwd=self.workspace_root,
            )
        else:
            # Shell script or other
            result = subprocess.run(
                ["sh", str(playbook_path)] + (list(args.values()) if args else []),
                capture_output=True,
                text=True,
                cwd=self.workspace_root,
            )

        if result.returncode != 0:
            logger.error(f"Playbook execution failed: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, playbook_path, result.stderr)

        return {
            "success": True,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }


"""
Context Builder - Builds context for activity prompts

Loads specification, manifest, tools, and history for context injection.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from .state import ActivityHistory, Manifest, Specification

logger = logging.getLogger(__name__)


class ContextBuilder:
    """
    Builds context for activity prompts.
    
    Loads:
    - Specification (user's goals/requirements)
    - Manifest (current state/outputs)
    - Tools (available playbooks)
    - History (past decisions/outcomes)
    """

    def __init__(self, workspace_root: Optional[Path] = None):
        """
        Initialize context builder.
        
        Args:
            workspace_root: SPECTRA workspace root directory. If None, auto-detects.
        """
        self.workspace_root = workspace_root or self._find_workspace_root()

    def _find_workspace_root(self) -> Path:
        """
        Find SPECTRA workspace root directory.
        
        Strategies:
        1. Check for .spectra marker in current/parent directories
        2. Check for Core/ directory structure
        
        Returns:
            Path to workspace root
            
        Raises:
            ValueError: If workspace root cannot be found
        """
        current = Path.cwd()

        # Strategy 1: Check for .spectra marker
        for check_path in [current] + list(current.parents):
            if (check_path / ".spectra").exists():
                logger.debug(f"Found workspace root via .spectra marker: {check_path}")
                return check_path

        # Strategy 2: Check for Core/ directory (assuming we're in Core/orchestrator)
        for check_path in [current] + list(current.parents):
            if (check_path / "Core").exists() and check_path.name != "Core":
                logger.debug(f"Found workspace root via Core/ directory: {check_path}")
                return check_path
            # If we're in Core/orchestrator, workspace root is parent of Core
            if check_path.name == "Core":
                workspace_root = check_path.parent
                logger.debug(f"Found workspace root (parent of Core): {workspace_root}")
                return workspace_root

        raise ValueError("Could not find SPECTRA workspace root")

    def load_specification(self, service_name: str) -> Optional[Specification]:
        """
        Load specification for a service.
        
        Args:
            service_name: Service name
            
        Returns:
            Specification object, or None if not found
        """
        # Try .spectra/ directory first
        spectra_dir = self.workspace_root / ".spectra"
        spec_path = spectra_dir / f"{service_name}.specification.yaml"
        if spec_path.exists():
            logger.debug(f"Loading specification from: {spec_path}")
            return Specification.load(spec_path)

        # Try service directory (e.g., Core/{service_name}/{service_name}.specification.yaml)
        service_paths = [
            self.workspace_root / "Core" / service_name / f"{service_name}.specification.yaml",
            self.workspace_root / service_name / f"{service_name}.specification.yaml",
        ]
        for spec_path in service_paths:
            if spec_path.exists():
                logger.debug(f"Loading specification from: {spec_path}")
                return Specification.load(spec_path)

        logger.warning(f"Specification not found for service: {service_name}")
        return None

    def load_manifest(self, service_name: str, activity_name: str) -> Optional[Manifest]:
        """
        Load manifest for an activity.
        
        Args:
            service_name: Service name
            activity_name: Activity name (e.g., "discover")
            
        Returns:
            Manifest object, or None if not found
        """
        # Try .spectra/manifests/ directory
        manifests_dir = self.workspace_root / ".spectra" / "manifests"
        manifest_path = manifests_dir / f"{activity_name}-manifest.yaml"
        if manifest_path.exists():
            logger.debug(f"Loading manifest from: {manifest_path}")
            return Manifest.load(manifest_path)

        # Try service-specific manifest
        service_paths = [
            self.workspace_root / ".spectra" / service_name / f"{activity_name}-manifest.yaml",
            self.workspace_root / "Core" / service_name / f"{activity_name}-manifest.yaml",
        ]
        for manifest_path in service_paths:
            if manifest_path.exists():
                logger.debug(f"Loading manifest from: {manifest_path}")
                return Manifest.load(manifest_path)

        logger.debug(f"Manifest not found for {activity_name}, will create new one")
        return None

    def load_tools(self, activity_name: str) -> List[Dict]:
        """
        Load available tools/playbooks for an activity.
        
        Args:
            activity_name: Activity name
            
        Returns:
            List of tool/playbook definitions
        """
        # TODO: Load from playbook registry when implemented
        # For now, return empty list
        logger.debug(f"Loading tools for activity: {activity_name}")
        return []

    def load_history(self, activity_name: str) -> ActivityHistory:
        """
        Load activity history for self-learning.
        
        Args:
            activity_name: Activity name
            
        Returns:
            ActivityHistory object (empty if not found)
        """
        history_dir = self.workspace_root / ".spectra" / "history"
        history_path = history_dir / f"{activity_name}-history.yaml"
        
        logger.debug(f"Loading history from: {history_path}")
        return ActivityHistory.load(history_path)

    def build_activity_context(
        self,
        activity_name: str,
        service_name: Optional[str] = None,
        specification: Optional[Specification] = None,
        manifest: Optional[Manifest] = None,
        tools: Optional[List[Dict]] = None,
        history: Optional[ActivityHistory] = None,
    ) -> Dict:
        """
        Build complete context for an activity.
        
        Args:
            activity_name: Activity name
            service_name: Service name (used to load specification/manifest if not provided)
            specification: Specification object (loaded if not provided)
            manifest: Manifest object (loaded if not provided)
            tools: List of tools (loaded if not provided)
            history: ActivityHistory object (loaded if not provided)
            
        Returns:
            Context dictionary
        """
        if service_name:
            if specification is None:
                specification = self.load_specification(service_name)
            if manifest is None:
                manifest = self.load_manifest(service_name, activity_name)
        
        if tools is None:
            tools = self.load_tools(activity_name)
        
        if history is None:
            history = self.load_history(activity_name)

        context = {
            "activity": activity_name,
            "specification": specification.to_dict() if specification else None,
            "manifest": manifest.to_dict() if manifest else None,
            "tools": tools,
            "history": [entry.__dict__ for entry in history.get_recent(10)] if history else [],
        }

        return context


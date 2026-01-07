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
        self._orchestrator_dir = self._find_orchestrator_dir()
    
    def _find_orchestrator_dir(self) -> Optional[Path]:
        """
        Find orchestrator repository directory.
        
        Returns:
            Path to Core/orchestrator/ if found, None otherwise
        """
        orchestrator_path = self.workspace_root / "Core" / "orchestrator"
        if orchestrator_path.exists():
            return orchestrator_path
        return None
    
    @property
    def orchestrator_state_dir(self) -> Path:
        """
        Get directory for orchestrator internal state.
        
        Returns:
            Path to .orchestrator/ directory in orchestrator repo
        """
        if self._orchestrator_dir:
            return self._orchestrator_dir / ".orchestrator"
        # Fallback to workspace root if orchestrator not found
        return self.workspace_root / ".spectra" / "orchestrator"

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

        # Strategy 1: Check for Core/ directory (primary method - more reliable)
        for check_path in [current] + list(current.parents):
            if (check_path / "Core").exists() and check_path.name != "Core":
                logger.debug(f"Found workspace root via Core/ directory: {check_path}")
                return check_path
            # If we're in Core/orchestrator, workspace root is parent of Core
            if check_path.name == "Core":
                workspace_root = check_path.parent
                logger.debug(f"Found workspace root (parent of Core): {workspace_root}")
                return workspace_root

        # Strategy 2: Fallback to .spectra marker (for solution-engine compatibility)
        for check_path in [current] + list(current.parents):
            if (check_path / ".spectra").exists():
                logger.debug(f"Found workspace root via .spectra marker (fallback): {check_path}")
                return check_path

        raise ValueError("Could not find SPECTRA workspace root")

    def load_specification(self, service_name: str) -> Optional[Specification]:
        """
        Load specification for a service.
        
        SPECTRA-Grade: Specifications are stored in service directories following Service Blueprint.
        
        Args:
            service_name: Service name
            
        Returns:
            Specification object, or None if not found
        """
        # Try service directories first (SPECTRA-Grade location)
        for org_folder in ["Core", "Data", "Design", "Engagement", "Engineering", "Media", "Security"]:
            spec_path = self.workspace_root / org_folder / service_name / f"{service_name}.specification.yaml"
            if spec_path.exists():
                logger.debug(f"Loading specification from: {spec_path}")
                return Specification.load(spec_path)

        # Fallback to .spectra/ (legacy solution-engine location)
        spectra_dir = self.workspace_root / ".spectra" / "specifications"
        spec_path = spectra_dir / f"{service_name}-specification.yaml"
        if spec_path.exists():
            logger.debug(f"Loading specification from legacy location: {spec_path}")
            return Specification.load(spec_path)

        logger.warning(f"Specification not found for service: {service_name}")
        return None

    def load_manifest(self, service_name: str, activity_name: str) -> Optional[Manifest]:
        """
        Load manifest for an activity.
        
        SPECTRA-Grade: Manifests are stored in orchestrator repo, not workspace root.
        
        Args:
            service_name: Service name
            activity_name: Activity name (e.g., "discover")
            
        Returns:
            Manifest object, or None if not found
        """
        # Orchestrator state stored in orchestrator repo
        manifests_dir = self.orchestrator_state_dir / "manifests"
        manifest_path = manifests_dir / f"{activity_name}-manifest.yaml"
        if manifest_path.exists():
            logger.debug(f"Loading manifest from orchestrator state: {manifest_path}")
            return Manifest.load(manifest_path)

        # Fallback to .spectra/ (legacy solution-engine location)
        legacy_path = self.workspace_root / ".spectra" / "manifests" / f"{activity_name}-manifest.yaml"
        if legacy_path.exists():
            logger.debug(f"Loading manifest from legacy location: {legacy_path}")
            return Manifest.load(legacy_path)

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
        
        SPECTRA-Grade: History stored in orchestrator repo, not workspace root.
        
        Args:
            activity_name: Activity name
            
        Returns:
            ActivityHistory object (empty if not found)
        """
        # Orchestrator state stored in orchestrator repo
        history_dir = self.orchestrator_state_dir / "history"
        history_path = history_dir / f"{activity_name}-history.yaml"
        
        logger.debug(f"Loading history from orchestrator state: {history_path}")
        return ActivityHistory.load(history_path)

    def summarize_specification(self, specification: Optional[Specification]) -> Optional[str]:
        """
        Summarize specification to reduce prompt size.
        
        Args:
            specification: Specification object
            
        Returns:
            Summarized specification string, or None
        """
        if not specification:
            return None
        
        spec_dict = specification.to_dict()
        summary_parts = []
        
        if spec_dict.get("service"):
            summary_parts.append(f"Service: {spec_dict['service']}")
        if spec_dict.get("purpose"):
            summary_parts.append(f"Purpose: {spec_dict['purpose'][:200]}...")
        if spec_dict.get("maturity"):
            summary_parts.append(f"Maturity: {spec_dict['maturity']}")
        
        return "\n".join(summary_parts) if summary_parts else None

    def summarize_manifest(self, manifest: Optional[Manifest]) -> Optional[str]:
        """
        Summarize manifest to reduce prompt size.
        
        Args:
            manifest: Manifest object
            
        Returns:
            Summarized manifest string, or None
        """
        if not manifest:
            return None
        
        manifest_dict = manifest.to_dict()
        summary_parts = []
        
        if manifest_dict.get("status"):
            summary_parts.append(f"Status: {manifest_dict['status']}")
        if manifest_dict.get("outputs"):
            outputs = manifest_dict["outputs"]
            output_keys = list(outputs.keys())[:5]  # First 5 keys only
            summary_parts.append(f"Outputs: {', '.join(output_keys)}")
        
        return "\n".join(summary_parts) if summary_parts else None

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

        # Summarize instead of full dump to reduce prompt size
        context = {
            "activity": activity_name,
            "specification_summary": self.summarize_specification(specification),
            "manifest_summary": self.summarize_manifest(manifest),
            "tools": tools[:10] if tools else [],  # Limit to 10 tools
            "history_count": len(history.get_recent(10)) if history else 0,
        }

        return context


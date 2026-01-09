"""
Context Builder - Builds context for activity prompts

Loads specification, manifest, tools, and history for context injection.
"""

import json
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
        # Important: .spectra may be in Core/, so parent is workspace root
        for check_path in [current] + list(current.parents):
            if (check_path / ".spectra").exists():
                # If .spectra is in a directory named "Core", the parent is workspace root
                if check_path.name == "Core":
                    parent = check_path.parent
                    if (parent / "Data").exists():
                        logger.debug(f"Found workspace root via .spectra in Core/: {parent}")
                        return parent
                # Otherwise, verify it's the root (has Core/ and Data/)
                elif (check_path / "Core").exists() and (check_path / "Data").exists():
                    logger.debug(f"Found workspace root via .spectra marker: {check_path}")
                    return check_path

        # Strategy 2: Check for Core/ directory structure
        # Workspace root contains Core/, not is Core/
        for check_path in [current] + list(current.parents):
            # If we're inside Core/, the parent is workspace root
            if check_path.name == "Core":
                parent = check_path.parent
                if (parent / "Data").exists():
                    logger.debug(f"Found workspace root via Core/ directory: {parent}")
                    return parent
            # If this path contains both Core/ and Data/, it's the root
            elif (check_path / "Core").exists() and (check_path / "Data").exists():
                logger.debug(f"Found workspace root via Core/Data directories: {check_path}")
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
        from .playbooks import PlaybookRegistry

        logger.debug(f"Loading tools for activity: {activity_name}")

        registry = PlaybookRegistry(workspace_root=self.workspace_root)
        playbooks = registry.discover_playbooks(activity_name)

        return [
            {
                "name": pb.name,
                "description": pb.description,
                "path": pb.path,
                "domain": pb.metadata.get("domain", "unknown"),
                "inputs": pb.inputs or [],
                "outputs": pb.outputs or [],
            }
            for pb in playbooks
        ]

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

    def load_idea(self, idea_id: Optional[str] = None, idea_name: Optional[str] = None) -> Optional[Dict]:
        """
        Load idea from Labs queue.

        Args:
            idea_id: Idea ID (e.g., "powerapp-service-catalog-client-manager-001")
            idea_name: Idea name (alternative search)

        Returns:
            Idea dictionary, or None if not found
        """
        ideas_path = self.workspace_root / "Core" / "labs" / "queue" / "ideas.json"

        if not ideas_path.exists():
            logger.debug(f"Ideas queue not found at: {ideas_path}")
            return None

        try:
            with open(ideas_path, 'r', encoding='utf-8') as f:
                ideas_data = json.load(f)

            ideas = ideas_data.get("ideas", [])

            # Search by ID first
            if idea_id:
                for idea in ideas:
                    if idea.get("id") == idea_id:
                        logger.debug(f"Found idea by ID: {idea_id}")
                        return idea

            # Search by name
            if idea_name:
                for idea in ideas:
                    if idea.get("name") == idea_name or idea_name in idea.get("name", ""):
                        logger.debug(f"Found idea by name: {idea_name}")
                        return idea

            # Search in user input context (could be enhanced)
            logger.debug("Idea not found by ID or name")
            return None

        except Exception as e:
            logger.warning(f"Failed to load ideas: {e}")
            return None

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

        # Load idea context if available (for Labs queue ideas)
        idea_context = None
        if service_name:
            # Try to find idea by name
            idea_context = self.load_idea(idea_name=service_name)

        # Summarize instead of full dump to reduce prompt size
        context = {
            "activity": activity_name,
            "specification_summary": self.summarize_specification(specification),
            "manifest_summary": self.summarize_manifest(manifest),
            "tools": tools[:10] if tools else [],  # Limit to 10 tools
            "history_count": len(history.get_recent(10)) if history else 0,
        }

        # Add idea context if found
        if idea_context:
            context["idea"] = {
                "id": idea_context.get("id"),
                "name": idea_context.get("name"),
                "purpose": idea_context.get("purpose", "")[:500],  # Limit length
                "type": idea_context.get("type"),
                "notes": idea_context.get("notes", "")[:1000] if idea_context.get("notes") else None,
            }
            logger.debug(f"Included idea context: {idea_context.get('name')}")

        return context


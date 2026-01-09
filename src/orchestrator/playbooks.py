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
                    # If .spectra is in Core/, parent is workspace root
                    if check_path.name == "Core":
                        workspace_root = check_path.parent
                    else:
                        workspace_root = check_path
                    break
                if check_path.name == "Core":
                    workspace_root = check_path.parent
                    break

        # Ensure workspace_root is the actual root (contains Core/, not is Core/)
        if workspace_root and workspace_root.name == "Core":
            workspace_root = workspace_root.parent

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

    async def filter_relevant_playbooks(
        self,
        activity_name: str,
        task: str,
        llm_client,
        max_playbooks: int = 5,
        use_embeddings: bool = True,
    ) -> List[Playbook]:
        """
        Filter playbooks to most relevant using semantic filtering.

        Uses embedding search if available (fast), otherwise falls back to LLM filtering.

        Args:
            activity_name: Activity name (e.g., "provision")
            task: User task description
            llm_client: LLM client for filtering (fallback if embeddings unavailable)
            max_playbooks: Maximum playbooks to return (default: 5)
            use_embeddings: Try embedding search first (default: True)

        Returns:
            List of filtered playbooks (most relevant)
        """
        from .embeddings import is_available as embeddings_available, EmbeddingSearch

        # Get all playbooks for activity
        all_playbooks = self.discover_playbooks(activity_name)

        if not all_playbooks:
            logger.warning(f"No playbooks found for activity: {activity_name}")
            return []

        # If we have few playbooks, no need to filter
        if len(all_playbooks) <= max_playbooks:
            logger.debug(f"Playbook count ({len(all_playbooks)}) <= max ({max_playbooks}), skipping filter")
            return all_playbooks

        # Try embedding search first if available and enabled
        if use_embeddings and embeddings_available():
            try:
                logger.info("Using embedding search for playbook filtering")
                embedding_search = EmbeddingSearch(workspace_root=self.workspace_root)

                # Load cache
                embedding_search.load_cache()

                # Search using embeddings
                filtered_playbooks = embedding_search.search_playbooks(
                    query=task,
                    all_playbooks=all_playbooks,
                    top_k=max_playbooks,
                )

                logger.info(f"Embedding search selected {len(filtered_playbooks)} playbooks")
                return filtered_playbooks

            except Exception as e:
                logger.warning(f"Embedding search failed: {e}, falling back to LLM filtering")
                # Fall through to LLM filtering

        # Fallback to LLM filtering
        logger.info("Using LLM filtering for playbook selection")
        from .semantic_filter import SemanticFilter

        semantic_filter = SemanticFilter(llm_client=llm_client, max_items=max_playbooks)
        filtered_playbooks = await semantic_filter.filter_playbooks(
            activity_name=activity_name,
            task=task,
            all_playbooks=all_playbooks,
            max_playbooks=max_playbooks,
        )

        return filtered_playbooks

    def get_playbook_context_for_llm(self, activity_name: str, playbooks: Optional[List[Playbook]] = None) -> Dict:
        """
        Get optimized context for LLM (metadata only - for selection).

        Provides playbook metadata suitable for LLM context without loading
        full playbook content (JIT loading pattern).

        Args:
            activity_name: Activity name (e.g., "deploy")
            playbooks: Optional pre-filtered playbooks. If None, discovers all playbooks.

        Returns:
            Dictionary with playbook metadata suitable for LLM context
        """
        if playbooks is None:
            playbooks = self.discover_playbooks(activity_name)

        return {
            "available_playbooks": [
                {
                    "name": pb.name,
                    "domain": pb.metadata.get("domain", "unknown"),
                    "description": pb.description,
                    "summary": pb.metadata.get("summary", pb.description),
                    "path": pb.path,  # Relative path (e.g., "railway/railway.001-create-service.md")
                    "full_path": f"Core/operations/playbooks/{pb.path}",  # Full path for codebase access
                    "inputs": pb.inputs or [],
                    "outputs": pb.outputs or [],
                    "mcp_native": pb.metadata.get("mcp_native", False),
                    "manual_steps": pb.metadata.get("manual_steps", False),
                    "automation_possible": pb.metadata.get("automation_possible", True),
                }
                for pb in playbooks
            ],
            "instructions": (
                "To access a playbook's full content, use the read_file tool with the full_path. "
                "You can also use codebase_search to find related playbooks or search for specific instructions."
            )
        }


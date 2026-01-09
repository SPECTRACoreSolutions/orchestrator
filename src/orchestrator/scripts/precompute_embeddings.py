"""
Pre-compute playbook embeddings for fast semantic search

Run this script after adding/modifying playbooks to update the embeddings cache.

Usage:
    python precompute_embeddings.py [--workspace-root PATH] [--model MODEL_NAME]
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator.embeddings import EmbeddingSearch, is_available
from orchestrator.playbooks import PlaybookRegistry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Pre-compute embeddings for all playbooks in registry."""
    parser = argparse.ArgumentParser(
        description="Pre-compute playbook embeddings for semantic search"
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        help="SPECTRA workspace root directory (auto-detects if not provided)",
    )
    parser.add_argument(
        "--model",
        default="all-MiniLM-L6-v2",
        help="Sentence-transformers model name (default: all-MiniLM-L6-v2)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force recompute even if embeddings exist",
    )

    args = parser.parse_args()

    # Check if embeddings are available
    if not is_available():
        logger.error("sentence-transformers not available!")
        logger.error("Install with: pip install sentence-transformers torch scikit-learn")
        return 1

    try:
        # Initialize embedding search
        logger.info(f"Initializing EmbeddingSearch with model: {args.model}")
        embedding_search = EmbeddingSearch(
            model_name=args.model,
            workspace_root=args.workspace_root,
        )

        # Load existing cache (unless force)
        if not args.force:
            logger.info("Loading existing cache...")
            embedding_search.load_cache()
        else:
            logger.info("Force mode: recomputing all embeddings")

        # Load playbook registry
        logger.info("Loading playbook registry...")
        playbook_registry = PlaybookRegistry(workspace_root=args.workspace_root)
        registry_data = playbook_registry.load_registry()

        # Get all playbooks
        all_playbooks = []
        for activity in ["engage", "discover", "plan", "assess", "design", "provision", "build", "test", "deploy", "monitor", "optimise", "finalise"]:
            playbooks = playbook_registry.discover_playbooks(activity)
            all_playbooks.extend(playbooks)

        logger.info(f"Found {len(all_playbooks)} total playbooks across all activities")

        if not all_playbooks:
            logger.warning("No playbooks found in registry!")
            return 0

        # Pre-compute embeddings
        logger.info("Computing embeddings...")
        count = embedding_search.precompute_playbook_embeddings(all_playbooks)

        # Save cache
        logger.info("Saving embeddings cache...")
        embedding_search.save_cache()

        logger.info(f"✓ Successfully computed and cached {count} playbook embeddings")
        logger.info(f"Cache saved to: {embedding_search.cache_path}")

        return 0

    except Exception as e:
        logger.error(f"Failed to precompute embeddings: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())


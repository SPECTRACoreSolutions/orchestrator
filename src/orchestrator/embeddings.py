"""
Embedding Search - Semantic search using sentence embeddings

Industry-standard approach using sentence-transformers for fast, accurate semantic search.
Replaces LLM calls with ~1ms cosine similarity search.

Pattern: Pre-compute embeddings, cache, fast lookup (industry standard from OpenAI, Cohere, etc.)
"""

import logging
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Optional imports - degrade gracefully if not available
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    logger.warning("sentence-transformers or scikit-learn not available - embedding search disabled")
    EMBEDDINGS_AVAILABLE = False
    SentenceTransformer = None
    cosine_similarity = None


class EmbeddingSearch:
    """
    Embedding-based semantic search for playbooks and context.

    Uses sentence-transformers for embedding generation and cosine similarity
    for fast semantic search (~1-5ms vs ~200-500ms for LLM).

    Pattern: Pre-compute, cache, fast lookup (industry standard)
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        cache_dir: Optional[Path] = None,
        workspace_root: Optional[Path] = None,
    ):
        """
        Initialize embedding search.

        Args:
            model_name: Sentence-transformers model name (default: all-MiniLM-L6-v2 - fast, 384 dims)
            cache_dir: Directory to cache embeddings (default: .spectra/embeddings/)
            workspace_root: Workspace root for cache location
        """
        if not EMBEDDINGS_AVAILABLE:
            raise ImportError(
                "sentence-transformers and scikit-learn required for embedding search. "
                "Install with: pip install sentence-transformers scikit-learn torch"
            )

        self.model_name = model_name
        self.model: Optional[SentenceTransformer] = None

        # Determine cache directory
        if cache_dir is None:
            if workspace_root is None:
                workspace_root = self._find_workspace_root()
            cache_dir = workspace_root / ".spectra" / "embeddings"

        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.embeddings_cache: Dict[str, np.ndarray] = {}
        self.cache_path = self.cache_dir / "playbooks.pkl"

        logger.info(f"Initialized EmbeddingSearch with model: {model_name}")

    def _find_workspace_root(self) -> Path:
        """Find SPECTRA workspace root."""
        current = Path.cwd()
        for check_path in [current] + list(current.parents):
            if (check_path / ".spectra").exists():
                if check_path.name == "Core":
                    return check_path.parent
                return check_path
            if check_path.name == "Core":
                return check_path.parent
        raise ValueError("Could not find SPECTRA workspace root")

    def _load_model(self):
        """Lazy load sentence-transformers model."""
        if self.model is None:
            logger.info(f"Loading sentence-transformers model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info("Model loaded successfully")

    def load_cache(self) -> bool:
        """
        Load embeddings cache from disk.

        Returns:
            True if cache loaded successfully, False otherwise
        """
        if not self.cache_path.exists():
            logger.debug(f"Embeddings cache not found: {self.cache_path}")
            return False

        try:
            with open(self.cache_path, "rb") as f:
                cache_data = pickle.load(f)

            self.embeddings_cache = cache_data.get("embeddings", {})
            model_name = cache_data.get("model_name")

            if model_name != self.model_name:
                logger.warning(f"Cache model ({model_name}) != current model ({self.model_name}), invalidating cache")
                self.embeddings_cache = {}
                return False

            logger.info(f"Loaded {len(self.embeddings_cache)} embeddings from cache")
            return True

        except Exception as e:
            logger.error(f"Failed to load embeddings cache: {e}")
            self.embeddings_cache = {}
            return False

    def save_cache(self):
        """Save embeddings cache to disk."""
        try:
            cache_data = {
                "model_name": self.model_name,
                "embeddings": self.embeddings_cache,
            }

            with open(self.cache_path, "wb") as f:
                pickle.dump(cache_data, f)

            logger.info(f"Saved {len(self.embeddings_cache)} embeddings to cache")

        except Exception as e:
            logger.error(f"Failed to save embeddings cache: {e}")

    def embed_text(self, text: str) -> np.ndarray:
        """
        Generate embedding for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector (numpy array)
        """
        self._load_model()
        return self.model.encode(text, convert_to_numpy=True)

    def embed_playbook(self, playbook) -> np.ndarray:
        """
        Generate embedding for playbook.

        Combines name, description, and domain for rich semantic representation.

        Args:
            playbook: Playbook object

        Returns:
            Embedding vector
        """
        # Check cache first
        cache_key = playbook.name
        if cache_key in self.embeddings_cache:
            return self.embeddings_cache[cache_key]

        # Build text representation
        text_parts = [
            playbook.name,
            playbook.description,
            playbook.metadata.get("domain", ""),
            playbook.metadata.get("summary", ""),
        ]
        text = " ".join(part for part in text_parts if part)

        # Generate embedding
        embedding = self.embed_text(text)

        # Cache it
        self.embeddings_cache[cache_key] = embedding

        return embedding

    def precompute_playbook_embeddings(self, playbooks: List) -> int:
        """
        Pre-compute embeddings for all playbooks.

        Args:
            playbooks: List of Playbook objects

        Returns:
            Number of embeddings computed
        """
        logger.info(f"Pre-computing embeddings for {len(playbooks)} playbooks...")

        count = 0
        for playbook in playbooks:
            # embed_playbook will cache automatically
            self.embed_playbook(playbook)
            count += 1

        logger.info(f"Computed {count} embeddings")
        return count

    def search_playbooks(
        self,
        query: str,
        all_playbooks: List,
        top_k: int = 5,
    ) -> List:
        """
        Search for most relevant playbooks using cosine similarity.

        Args:
            query: Search query (user task)
            all_playbooks: All available playbooks
            top_k: Number of results to return

        Returns:
            List of top-k most relevant playbooks
        """
        if not all_playbooks:
            return []

        if len(all_playbooks) <= top_k:
            return all_playbooks

        logger.debug(f"Searching {len(all_playbooks)} playbooks for query: {query[:100]}...")

        # Generate query embedding
        query_embedding = self.embed_text(query)

        # Get playbook embeddings (from cache or compute)
        playbook_embeddings = []
        for playbook in all_playbooks:
            embedding = self.embed_playbook(playbook)
            playbook_embeddings.append(embedding)

        # Compute cosine similarity
        playbook_embeddings_matrix = np.array(playbook_embeddings)
        similarities = cosine_similarity([query_embedding], playbook_embeddings_matrix)[0]

        # Get top-k indices
        top_k_indices = similarities.argsort()[-top_k:][::-1]

        # Return top-k playbooks
        top_k_playbooks = [all_playbooks[i] for i in top_k_indices]

        logger.info(f"Found top {len(top_k_playbooks)} playbooks: {[pb.name for pb in top_k_playbooks]}")
        logger.debug(f"Similarities: {[similarities[i] for i in top_k_indices]}")

        return top_k_playbooks

    def search_items(
        self,
        query: str,
        items: List[Dict],
        item_text_key: str = "description",
        top_k: int = 5,
    ) -> List[Tuple[Dict, float]]:
        """
        Generic semantic search for any list of items.

        Args:
            query: Search query
            items: List of items (dictionaries)
            item_text_key: Key to use for text representation
            top_k: Number of results to return

        Returns:
            List of (item, similarity_score) tuples
        """
        if not items:
            return []

        if len(items) <= top_k:
            return [(item, 1.0) for item in items]

        # Generate query embedding
        query_embedding = self.embed_text(query)

        # Generate item embeddings
        item_embeddings = []
        for item in items:
            text = item.get(item_text_key, str(item))
            embedding = self.embed_text(text)
            item_embeddings.append(embedding)

        # Compute cosine similarity
        item_embeddings_matrix = np.array(item_embeddings)
        similarities = cosine_similarity([query_embedding], item_embeddings_matrix)[0]

        # Get top-k indices
        top_k_indices = similarities.argsort()[-top_k:][::-1]

        # Return top-k items with scores
        results = [
            (items[i], float(similarities[i]))
            for i in top_k_indices
        ]

        return results


def is_available() -> bool:
    """
    Check if embedding search is available.

    Returns:
        True if sentence-transformers and scikit-learn are installed
    """
    return EMBEDDINGS_AVAILABLE


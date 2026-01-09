"""
Performance benchmarks for embedding search

Compares:
- LLM filtering latency (~200-500ms)
- Embedding search latency (~1-5ms)
- Memory usage
- Accuracy (qualitative)
"""

import pytest
import time
from unittest.mock import AsyncMock, MagicMock

from orchestrator.embeddings import EmbeddingSearch, is_available
from orchestrator.semantic_filter import SemanticFilter
from orchestrator.playbooks import Playbook


# Skip tests if embeddings not available
pytestmark = pytest.mark.skipif(
    not is_available(),
    reason="sentence-transformers not available"
)


@pytest.fixture
def large_playbook_set():
    """Create a large set of playbooks for benchmarking."""
    playbooks = []
    domains = ["railway", "github", "docker", "kubernetes", "terraform", "ansible", "azure", "aws", "gcp"]
    activities = ["provision", "build", "deploy", "test", "monitor"]

    for i in range(100):
        domain = domains[i % len(domains)]
        activity = activities[i % len(activities)]

        playbooks.append(Playbook(
            name=f"{domain}.{i:03d}",
            description=f"Playbook for {domain} {activity} operations number {i}. " * 5,  # Long description
            path=f"{domain}/{domain}.{i:03d}.md",
            activity=activity,
            metadata={
                "domain": domain,
                "mcp_native": i % 2 == 0,
                "automation_possible": i % 3 != 0,
            },
        ))

    return playbooks


@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_llm_filtering_latency(large_playbook_set):
    """Benchmark LLM filtering latency."""
    # Mock LLM client with realistic delay
    mock_llm_client = MagicMock()

    async def mock_chat_completion(*args, **kwargs):
        await asyncio.sleep(0.3)  # Simulate 300ms LLM call
        return '{"selected_playbooks": ["railway.001", "railway.002", "railway.003"]}'

    mock_llm_client.chat_completion = mock_chat_completion

    semantic_filter = SemanticFilter(llm_client=mock_llm_client, max_items=5)

    start_time = time.time()
    result = await semantic_filter.filter_playbooks(
        activity_name="provision",
        task="Deploy to Railway",
        all_playbooks=large_playbook_set,
        max_playbooks=5,
    )
    elapsed = time.time() - start_time

    print(f"\nLLM filtering: {elapsed*1000:.1f}ms for {len(large_playbook_set)} playbooks")
    assert elapsed > 0.25  # Should take at least 250ms with LLM call


@pytest.mark.benchmark
def test_embedding_search_latency(large_playbook_set):
    """Benchmark embedding search latency."""
    embedding_search = EmbeddingSearch(model_name="all-MiniLM-L6-v2")

    # Pre-compute embeddings (one-time cost)
    precompute_start = time.time()
    embedding_search.precompute_playbook_embeddings(large_playbook_set)
    precompute_time = time.time() - precompute_start

    print(f"\nEmbedding pre-compute: {precompute_time*1000:.1f}ms for {len(large_playbook_set)} playbooks (one-time cost)")

    # Now test search latency (should be very fast)
    search_start = time.time()
    result = embedding_search.search_playbooks(
        query="Deploy to Railway",
        all_playbooks=large_playbook_set,
        top_k=5,
    )
    search_time = time.time() - search_start

    print(f"Embedding search: {search_time*1000:.1f}ms for {len(large_playbook_set)} playbooks")
    print(f"Speed improvement: {(300 / (search_time * 1000)):.1f}x faster than LLM")

    assert len(result) == 5
    assert search_time < 0.1  # Should be under 100ms (typically 1-5ms)


@pytest.mark.benchmark
def test_embedding_cache_effectiveness(large_playbook_set):
    """Test that caching improves performance on repeated searches."""
    embedding_search = EmbeddingSearch(model_name="all-MiniLM-L6-v2")

    # First search (no cache)
    start1 = time.time()
    result1 = embedding_search.search_playbooks(
        query="Deploy to Railway",
        all_playbooks=large_playbook_set,
        top_k=5,
    )
    time1 = time.time() - start1

    # Second search (with cache)
    start2 = time.time()
    result2 = embedding_search.search_playbooks(
        query="Build Docker container",
        all_playbooks=large_playbook_set,
        top_k=5,
    )
    time2 = time.time() - start2

    print(f"\nFirst search (no cache): {time1*1000:.1f}ms")
    print(f"Second search (cached): {time2*1000:.1f}ms")
    print(f"Cache speedup: {(time1/time2):.1f}x")

    # Second search should be faster (cached embeddings)
    assert time2 <= time1


@pytest.mark.benchmark
def test_embedding_memory_usage(large_playbook_set):
    """Test memory usage of embedding cache."""
    import sys

    embedding_search = EmbeddingSearch(model_name="all-MiniLM-L6-v2")

    # Measure before
    initial_size = sys.getsizeof(embedding_search.embeddings_cache)

    # Pre-compute embeddings
    embedding_search.precompute_playbook_embeddings(large_playbook_set)

    # Measure after
    final_size = sys.getsizeof(embedding_search.embeddings_cache)
    cache_size_mb = (final_size - initial_size) / (1024 * 1024)

    print(f"\nCache size for {len(large_playbook_set)} playbooks: {cache_size_mb:.2f} MB")
    print(f"Per-playbook memory: {(cache_size_mb * 1024) / len(large_playbook_set):.2f} KB")

    # Reasonable memory usage (all-MiniLM-L6-v2 uses 384 dims, ~1.5KB per embedding)
    assert cache_size_mb < 1.0  # Should be under 1MB for 100 playbooks


@pytest.mark.benchmark
def test_embedding_accuracy_vs_llm(large_playbook_set):
    """
    Qualitative test: Compare embedding results with expected LLM results.

    Note: This is qualitative - embeddings and LLM may select different
    playbooks, but both should be relevant.
    """
    embedding_search = EmbeddingSearch(model_name="all-MiniLM-L6-v2")

    # Pre-compute embeddings
    embedding_search.precompute_playbook_embeddings(large_playbook_set)

    # Test query
    query = "Deploy service to Railway platform"
    result = embedding_search.search_playbooks(
        query=query,
        all_playbooks=large_playbook_set,
        top_k=5,
    )

    print(f"\nQuery: {query}")
    print(f"Top results:")
    for i, pb in enumerate(result, 1):
        print(f"  {i}. {pb.name} ({pb.metadata.get('domain')}) - {pb.description[:80]}...")

    # Should find railway playbooks near the top
    railway_count = sum(1 for pb in result if "railway" in pb.name.lower())
    print(f"Railway playbooks in top 5: {railway_count}")

    assert railway_count >= 1  # At least one railway playbook should be in top 5


@pytest.mark.benchmark
def test_scaling_performance(large_playbook_set):
    """Test how performance scales with playbook count."""
    embedding_search = EmbeddingSearch(model_name="all-MiniLM-L6-v2")

    # Test with different sizes
    sizes = [10, 50, 100]
    times = []

    for size in sizes:
        subset = large_playbook_set[:size]
        embedding_search.precompute_playbook_embeddings(subset)

        start = time.time()
        result = embedding_search.search_playbooks(
            query="Deploy to Railway",
            all_playbooks=subset,
            top_k=5,
        )
        elapsed = time.time() - start
        times.append(elapsed)

        print(f"\n{size} playbooks: {elapsed*1000:.1f}ms")

    # Performance should scale linearly (or better with cache)
    # 100 playbooks should not be 10x slower than 10 playbooks
    scaling_factor = times[-1] / times[0]
    print(f"Scaling factor (100x playbooks): {scaling_factor:.2f}x time")

    assert scaling_factor < 15  # Should scale reasonably well


if __name__ == "__main__":
    # Run benchmarks with output
    pytest.main([__file__, "-v", "-s", "-m", "benchmark"])


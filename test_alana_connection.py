#!/usr/bin/env python3
"""
Test Alana LLM connection for Orchestrator
"""

import asyncio
import sys
from pathlib import Path

# Add orchestrator to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from orchestrator.llm_client import LLMClient


async def test_alana():
    """Test Alana LLM connection."""
    print("Testing Alana LLM connection...")
    print(f"API URL: http://localhost:8001/v1/chat/completions")

    client = LLMClient()

    try:
        # Test health check
        print("\n1. Testing health check...")
        healthy = await client.health_check()

        if healthy:
            print("   [OK] Alana is healthy!")
        else:
            print("   [WARN] Health check returned False (service may still be loading model)")

        # Test actual API call
        print("\n2. Testing chat completion API...")
        try:
            response = await client.chat_completion(
                system_prompt="You are a helpful assistant.",
                user_message="Say 'Hello, Orchestrator!' if you can hear me.",
                max_tokens=50,
                temperature=0.3,
            )
            print(f"   [OK] API Response: {response[:100]}...")
            print("\n[SUCCESS] Alana is ready and responding!")
            return True
        except Exception as e:
            print(f"   [ERROR] API call failed: {e}")
            print("   (Model may still be loading - wait a bit longer)")
            return False

    except Exception as e:
        print(f"\n[ERROR] Connection error: {e}")
        print("   Make sure Alana is running: docker ps | findstr alana")
        return False
    finally:
        await client.close()


if __name__ == "__main__":
    success = asyncio.run(test_alana())
    sys.exit(0 if success else 1)


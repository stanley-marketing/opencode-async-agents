
import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

def test_sample_validation():
    """Sample test to validate E2E setup"""
    assert True

def test_imports():
    """Test that we can import required modules"""
    import json
    import time
    import threading
    assert True

@pytest.mark.asyncio
async def test_async_support():
    """Test async support"""
    import asyncio
    await asyncio.sleep(0.01)
    assert True

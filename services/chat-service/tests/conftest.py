"""
Pytest configuration for Chat Service
"""
import pytest
import sys
from pathlib import Path

# Add app directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

pytest_plugins = ['pytest_asyncio']

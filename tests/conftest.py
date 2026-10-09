"""Pytest configuration for hackathon tests."""
import sys
from pathlib import Path

# Ensure src is on path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Disable heavy imports
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
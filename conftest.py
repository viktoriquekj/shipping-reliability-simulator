# conftest.py
import sys
from pathlib import Path

# Add project root to Python path so pytest can find simulator/ and analysis/
sys.path.insert(0, str(Path(__file__).parent))
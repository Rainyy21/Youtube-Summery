import os
import sys
from pathlib import Path

# let tests do `from save import ...` like main.py does
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# summery.py exits on import without a key; tests never hit the real API
os.environ.setdefault("OPENROUTER_API_KEY", "test-key")

import json
from pathlib import Path

CONFIG_FILE = Path("~/.config/yt-summarizer/config.json").expanduser()
DEFAULT_DIR = "~/Documents/Notes"

def get_output_dir():
    """Return the saved output folder, or DEFAULT_DIR if none is set."""
    try:
        settings = json.loads(CONFIG_FILE.read_text())
        return settings.get("output_dir", DEFAULT_DIR)
    except (FileNotFoundError, json.JSONDecodeError):
        return DEFAULT_DIR

def set_output_dir(path):
    """Save a new output folder and return its full path."""
    full = str(Path(path).expanduser().resolve())
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps({"output_dir": full}, indent=2))
    return full

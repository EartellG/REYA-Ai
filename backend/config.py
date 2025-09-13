from pathlib import Path

# Only allow commits under this directory to avoid accidental writes elsewhere
REYA_REPOS_ROOT = Path("repos").resolve()
REYA_REPOS_ROOT.mkdir(parents=True, exist_ok=True)

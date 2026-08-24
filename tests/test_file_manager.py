import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.file_manager import create_workspace, cleanup_workspace


workspace = create_workspace()

print(f"Workspace created: {workspace}")

if not workspace.exists():
    raise AssertionError("Temporary workspace was not created.")

cleanup_workspace(workspace)

if workspace.exists():
    raise AssertionError("Temporary workspace was not removed.")

print("File manager successful.")
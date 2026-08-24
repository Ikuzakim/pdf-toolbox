import shutil
import tempfile
from pathlib import Path


def create_workspace():
    """Create a temporary workspace for one PDF operation."""
    return Path(tempfile.mkdtemp(prefix="pdf_toolbox_"))


def cleanup_workspace(workspace):
    """Remove a temporary workspace and all its contents."""
    if workspace and Path(workspace).exists():
        shutil.rmtree(workspace, ignore_errors=True)
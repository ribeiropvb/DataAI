import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def demo_dir(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("demo")
    subprocess.run([sys.executable, str(ROOT / "examples" / "generate_demo.py"), str(out)], check=True, capture_output=True)
    return out


@pytest.fixture
def workspace(tmp_path, demo_dir):
    from dataai.workspace import Workspace
    return Workspace.create(tmp_path, sorted(demo_dir.iterdir()), None, "both", "t")


def browser_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright
        from dataai.tools.inspect import launch_browser
        with sync_playwright() as p:
            launch_browser(p).close()
        return True
    except Exception:
        return False


ECHARTS = os.environ.get("DATAAI_ECHARTS_JS")

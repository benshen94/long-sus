from __future__ import annotations

import subprocess
import time
from pathlib import Path

from .config import PROJECT_ROOT
from .specs import DashboardArtifact


def _start_http_server(port: int) -> subprocess.Popen[str]:
    return subprocess.Popen(
        ["python3", "-m", "http.server", str(port)],
        cwd=PROJECT_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )


def _capture(url: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "npx",
        "--yes",
        "playwright",
        "screenshot",
        "--browser",
        "chromium",
        "--full-page",
        "--viewport-size",
        "1440,2200",
        "--wait-for-selector",
        "[data-ready='true']",
        "--wait-for-timeout",
        "1200",
        url,
        str(output_path),
    ]

    try:
        subprocess.run(command, check=True, timeout=180)
    except subprocess.CalledProcessError:
        subprocess.run(
            ["npx", "--yes", "playwright", "install", "chromium"],
            check=True,
            timeout=600,
        )
        subprocess.run(command, check=True, timeout=180)


def capture_dashboard_artifacts(
    *,
    base_url_path: str,
    overview_path: Path,
    comparison_path: Path,
    port: int = 8765,
) -> list[DashboardArtifact]:
    server = _start_http_server(port)
    time.sleep(1.0)

    try:
        overview_url = (
            f"http://127.0.0.1:{port}/{base_url_path}"
            "?preset=threshold_age_60_all_eligible&target=eta&factor=0.80&hetero=off"
            "&launch=2025&end=2100&uptake=threshold&threshold=60"
            "&comparePreset=no_one&compareTarget=none&compareFactor=1.00&compareHetero=off"
            "&year=2075"
        )
        comparison_url = (
            f"http://127.0.0.1:{port}/{base_url_path}"
            "?preset=prescription_bands_equal_probabilities&target=eta&factor=0.80&hetero=off"
            "&launch=2025&end=2100&uptake=banded&startRule=equal_probabilities"
            "&band2039=35&band4064=65&band65=95"
            "&comparePreset=prescription_bands_absolute&compareTarget=eta&compareFactor=0.80&compareHetero=off"
            "&year=2075"
        )

        _capture(overview_url, overview_path)
        _capture(comparison_url, comparison_path)

    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()

    return [
        DashboardArtifact(title="dashboard_overview", path=overview_path),
        DashboardArtifact(title="dashboard_comparison", path=comparison_path),
    ]

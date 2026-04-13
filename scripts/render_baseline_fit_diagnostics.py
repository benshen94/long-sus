from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIT_JSON_PATH = PROJECT_ROOT / "baseline_fits" / "country_baseline_fits_2024.json"
OUTPUT_DIR = PROJECT_ROOT / "baseline_fits"


plt.style.use("seaborn-v0_8-whitegrid")


def _survival_from_hazard(times: np.ndarray, hazard: np.ndarray) -> np.ndarray:
    survival = np.ones(len(times), dtype=float)

    for index in range(1, len(times)):
        dt = float(times[index] - times[index - 1])
        survival[index] = survival[index - 1] * np.exp(-float(hazard[index - 1]) * dt)

    return survival


def plot_country_fit_diagnostic(country_slug: str, payload: dict[str, object]) -> Path:
    target_times = np.asarray(payload["target_curve"]["times"], dtype=float)
    target_hazard = np.asarray(payload["target_curve"]["values"], dtype=float)
    fitted_hazard = np.asarray(payload["fitted_curve"]["values"], dtype=float)
    baseline_hazard = np.asarray(payload["baseline_curve"]["values"], dtype=float)

    target_survival = _survival_from_hazard(target_times, target_hazard)
    fitted_survival = _survival_from_hazard(target_times, fitted_hazard)
    baseline_survival = _survival_from_hazard(target_times, baseline_hazard)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))

    axes[0].plot(target_times, target_hazard, linewidth=2.7, color="#111111", label="Target")
    axes[0].plot(target_times, fitted_hazard, linewidth=2.3, color="#2a9d8f", label="Fitted")
    axes[0].plot(target_times, baseline_hazard, linewidth=2.0, color="#e76f51", linestyle="--", label="Baseline")
    axes[0].set_title("Hazard")
    axes[0].set_xlabel("Age")
    axes[0].set_ylabel("Annual hazard")
    axes[0].set_yscale("log")

    axes[1].plot(target_times, target_survival, linewidth=2.7, color="#111111", label="Target")
    axes[1].plot(target_times, fitted_survival, linewidth=2.3, color="#2a9d8f", label="Fitted")
    axes[1].plot(target_times, baseline_survival, linewidth=2.0, color="#e76f51", linestyle="--", label="Baseline")
    axes[1].set_title("Implied survival")
    axes[1].set_xlabel("Age")
    axes[1].set_ylabel("Survival from age 30")

    for ax in axes:
        ax.grid(True, which="both", alpha=0.25)
        ax.legend(loc="best")

    score = float(payload["score"])
    fit_year = int(payload["fit_year"])
    country_label = str(payload["country"])
    fig.suptitle(f"{country_label} {fit_year} SR fit diagnostics | score={score:.4f}", fontsize=15, weight="bold")
    fig.tight_layout()

    output_path = OUTPUT_DIR / f"{country_slug}_fit_diagnostic.png"
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return output_path


def render_all_fit_diagnostics(
    *,
    fit_json_path: Path = FIT_JSON_PATH,
    country_slugs: list[str] | None = None,
) -> list[Path]:
    payload = json.loads(fit_json_path.read_text())
    output_paths: list[Path] = []
    selected_slugs = set(country_slugs or [])

    for country_slug, country_payload in payload["countries"].items():
        if selected_slugs and country_slug not in selected_slugs:
            continue
        output_paths.append(plot_country_fit_diagnostic(country_slug, country_payload))

    return output_paths


def main() -> None:
    output_paths = render_all_fit_diagnostics()

    for path in output_paths:
        print(path)


if __name__ == "__main__":
    main()

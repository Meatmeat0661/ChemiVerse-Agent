"""Plot species abundances from westlake res.pickle (non-interactive)."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SAFE_NAME = re.compile(r"[^A-Za-z0-9._+-]+")


def _safe_filename(name: str) -> str:
    return SAFE_NAME.sub("_", name).strip("_") or "species"


def _plot_series(ax, res, name: str, t_start: float) -> None:
    mask = res.time > t_start
    ax.plot(res.time[mask], res[name][mask], label=name)


def _style_axes(ax, title: str) -> None:
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Time")
    ax.set_ylabel("Abundance")
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.25)


def plot_combined(res, species: list[str], output: Path, t_start: float) -> list[str]:
    fig, ax = plt.subplots(figsize=(9, 5.5))
    plotted: list[str] = []
    for name in species:
        _plot_series(ax, res, name, t_start)
        plotted.append(name)
    _style_axes(ax, "Westlake abundance evolution")
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=100)
    plt.close(fig)
    return plotted


def plot_separate(res, species: list[str], out_dir: Path, t_start: float) -> list[tuple[str, Path]]:
    written: list[tuple[str, Path]] = []
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in species:
        fig, ax = plt.subplots(figsize=(8, 5))
        _plot_series(ax, res, name, t_start)
        _style_axes(ax, f"{name} abundance evolution")
        fig.tight_layout()
        path = out_dir / f"{_safe_filename(name)}.png"
        fig.savefig(path, dpi=100)
        plt.close(fig)
        written.append((name, path))
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Plot westlake abundance evolution.")
    parser.add_argument("--dir", required=True, help="Simulation directory containing res.pickle")
    parser.add_argument(
        "--species",
        default="CO,CH3OH,CH3OCH3",
        help="Comma-separated species names in the Nautilus network",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory for PNG output (combined + per-species files)",
    )
    parser.add_argument(
        "--mode",
        choices=("combined", "separate", "both"),
        default="combined",
        help="combined: one figure; separate: one PNG per species; both",
    )
    parser.add_argument("--t-start", type=float, default=1.0, help="Minimum time for plotting")
    args = parser.parse_args()

    try:
        import westlake
    except ImportError:
        print("westlake package not installed in this Python environment.", file=sys.stderr)
        return 2

    sim_dir = Path(args.dir)
    res_path = sim_dir / "res.pickle"
    if not res_path.exists():
        print(f"Missing result file: {res_path}", file=sys.stderr)
        return 1

    res = westlake.load_result(res_path)
    available = set(res.species)
    requested = [name.strip() for name in args.species.split(",") if name.strip()]
    species = [name for name in requested if name in available]
    missing = [name for name in requested if name not in available]

    if not species:
        sample = ", ".join(list(res.species)[:25])
        print(
            f"No requested species found. Requested={requested}. "
            f"Available (first 25): {sample}",
            file=sys.stderr,
        )
        return 1

    out_dir = Path(args.output_dir)
    written_paths: list[Path] = []

    if args.mode in ("combined", "both"):
        combined = out_dir / "abundances.png"
        plot_combined(res, species, combined, args.t_start)
        written_paths.append(combined)
        print(f"Wrote {combined} ({', '.join(species)})")

    if args.mode in ("separate", "both"):
        for name, path in plot_separate(res, species, out_dir, args.t_start):
            written_paths.append(path)
            print(f"Wrote {path} ({name})")

    if missing:
        print(f"Skipped (not in network): {', '.join(missing)}", file=sys.stderr)

    print(f"MODE={args.mode} COUNT={len(written_paths)} DIR={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

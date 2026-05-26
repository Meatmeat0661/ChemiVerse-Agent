"""
在本机用 westlake 生成演化图，提交到 GitHub 后 Streamlit Cloud 可直接展示（无需服务器）。

用法:
  python scripts/publish_plots_to_repo.py --id nitrogen-default --species N2,NH3,HCN,H2CO

前提: 本机已安装 westlake，且 example_simulation 下已有 res.pickle（或加 --run 先跑模拟）。
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish westlake plots into data/plots for Streamlit Cloud")
    parser.add_argument("--id", required=True, help="Catalog entry id, e.g. nitrogen-default")
    parser.add_argument("--title", default="", help="Display title")
    parser.add_argument("--species", default="N2,NH3,HCN,H2CO")
    parser.add_argument("--plot-mode", default="both", choices=["both", "combined", "separate"])
    parser.add_argument("--sim-dir", default=None, help="Simulation dir name under tutorial_root")
    parser.add_argument("--run", action="store_true", help="Run westlake simulation before plotting")
    args = parser.parse_args()

    from backend.config import get_settings
    from backend.services.nautilus import NautilusRunner

    settings = get_settings()
    nautilus = NautilusRunner(settings.nautilus)
    species = [s.strip() for s in args.species.split(",") if s.strip()]
    plot_id = args.id
    out_dir = ROOT / "data" / "plots" / plot_id
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.run:
        print("Running westlake simulation (may take several minutes)...")
        result = nautilus.run(sim_dir=args.sim_dir, use_evolution=True, timeout=3600)
        if result["returncode"] != 0:
            raise SystemExit(f"Simulation failed: {result.get('stderr')}")

    sim_path = nautilus.simulation_dir(args.sim_dir)
    if not (sim_path / "res.pickle").exists():
        raise SystemExit(f"Missing {sim_path / 'res.pickle'}. Run with --run first.")

    print("Plotting...")
    plot_result = nautilus.plotter.plot(
        sim_dir=sim_path,
        species=species,
        run_id=plot_id,
        mode=args.plot_mode,
        include_images_base64=False,
    )
    if plot_result.get("returncode", 1) != 0:
        raise SystemExit(plot_result.get("stderr") or "Plot failed")

    api_out = Path(settings.nautilus.outputs_dir)
    if not api_out.is_absolute():
        api_out = ROOT / api_out
    src_dir = api_out / plot_id
    if src_dir.exists():
        for png in src_dir.glob("*.png"):
            shutil.copy2(png, out_dir / png.name)

    images = []
    for png in sorted(out_dir.glob("*.png")):
        label = "combined" if png.name == "abundances.png" else png.stem
        images.append({"label": label, "file": f"data/plots/{plot_id}/{png.name}"})

    catalog_path = ROOT / "data" / "simulation_catalog.json"
    catalog: list[dict] = []
    if catalog_path.exists():
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))

    entry = {
        "id": plot_id,
        "title": args.title or f"演化图 {plot_id}",
        "description": f"{', '.join(species)} · example_simulation",
        "species": species,
        "images": images,
    }
    catalog = [e for e in catalog if e.get("id") != plot_id] + [entry]
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {len(images)} PNG(s) to {out_dir}")
    print(f"Updated {catalog_path}")
    print("\nNext:")
    print(f"  git add data/plots/{plot_id} data/simulation_catalog.json")
    print("  git commit -m \"Add precomputed westlake plots\"")
    print("  git push")


if __name__ == "__main__":
    main()

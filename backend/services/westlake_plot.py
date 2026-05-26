from __future__ import annotations

import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from backend.config import NautilusSettings, ROOT

from backend.services.plot_images import attach_image_base64

PlotMode = Literal["combined", "separate", "both"]


class WestlakePlotter:
    def __init__(self, settings: NautilusSettings) -> None:
        self.settings = settings

    def outputs_root(self) -> Path:
        path = Path(self.settings.outputs_dir)
        if not path.is_absolute():
            path = ROOT / path
        path.mkdir(parents=True, exist_ok=True)
        return path

    def plot_script_path(self) -> Path:
        script = Path(self.settings.plot_script)
        if script.is_absolute():
            return script
        return ROOT / script

    def new_run_id(self) -> str:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        return f"{stamp}-{uuid.uuid4().hex[:8]}"

    def run_output_dir(self, run_id: str) -> Path:
        return self.outputs_root() / run_id

    def build_plot_command(
        self,
        sim_dir: Path,
        output_dir: Path,
        species: list[str] | None = None,
        mode: PlotMode | None = None,
        t_start: float | None = None,
    ) -> list[str]:
        species_csv = ",".join(species) if species else self.settings.default_species
        plot_mode = mode or self.settings.default_plot_mode
        cmd = [
            self.settings.python,
            str(self.plot_script_path()),
            f"--dir={sim_dir}",
            f"--species={species_csv}",
            f"--output-dir={output_dir}",
            f"--mode={plot_mode}",
        ]
        if t_start is not None:
            cmd.append(f"--t-start={t_start}")
        return cmd

    def _collect_images(self, run_id: str, output_dir: Path, mode: PlotMode) -> list[dict[str, str]]:
        images: list[dict[str, str]] = []
        combined = output_dir / "abundances.png"
        if mode in ("combined", "both") and combined.exists():
            images.append(
                {
                    "label": "combined",
                    "filename": combined.name,
                    "url": f"/api/outputs/{run_id}/{combined.name}",
                }
            )
        if mode in ("separate", "both"):
            for path in sorted(output_dir.glob("*.png")):
                if path.name == "abundances.png":
                    continue
                images.append(
                    {
                        "label": path.stem,
                        "filename": path.name,
                        "url": f"/api/outputs/{run_id}/{path.name}",
                    }
                )
        return images

    def plot(
        self,
        sim_dir: Path,
        species: list[str] | None = None,
        run_id: str | None = None,
        mode: PlotMode | None = None,
        t_start: float | None = None,
        include_images_base64: bool = False,
    ) -> dict[str, object]:
        script = self.plot_script_path()
        if not script.exists():
            raise FileNotFoundError(f"Plot script not found: {script}")

        run_id = run_id or self.new_run_id()
        plot_mode: PlotMode = mode or self.settings.default_plot_mode
        output_dir = self.run_output_dir(run_id)
        cmd = self.build_plot_command(
            sim_dir, output_dir, species=species, mode=plot_mode, t_start=t_start
        )

        completed = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        images = self._collect_images(run_id, output_dir, plot_mode) if completed.returncode == 0 else []
        if include_images_base64 and images:
            images = attach_image_base64(images, output_dir)
        primary_url = images[0]["url"] if images else None

        return {
            "command": cmd,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "run_id": run_id,
            "mode": plot_mode,
            "images": images,
            "image_url": primary_url,
            "plotted": species or self.settings.default_species.split(","),
        }

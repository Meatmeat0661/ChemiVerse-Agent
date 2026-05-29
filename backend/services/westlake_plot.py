from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from backend.config import NautilusSettings, ROOT
from backend.services.nautilus_env import resolve_python
from backend.services.plot_images import attach_image_base64

PlotMode = Literal["combined", "separate", "both"]


class WestlakePlotter:
    def __init__(self, settings: NautilusSettings) -> None:
        self.settings = settings

    def python_executable(self) -> str:
        plot_py = (self.settings.plot_python or "").strip()
        if plot_py:
            return resolve_python(plot_py)
        return sys.executable

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
            self.python_executable(),
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

    def _plot_cache_path(
        self,
        sim_dir: Path,
        *,
        plot_mode: PlotMode,
        species: list[str] | None,
        t_start: float | None,
    ) -> Path | None:
        pickle_path = sim_dir / "res.pickle"
        if not pickle_path.exists():
            return None
        species_csv = ",".join(species) if species else self.settings.default_species
        digest = hashlib.sha256(
            f"{pickle_path.stat().st_mtime_ns}|{plot_mode}|{species_csv}|{t_start}".encode()
        ).hexdigest()[:16]
        cache_dir = sim_dir / ".plot_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        if plot_mode == "combined":
            return cache_dir / f"combined_{digest}.png"
        if plot_mode == "separate":
            return cache_dir / f"separate_{digest}"
        return cache_dir / f"both_{digest}"

    def _try_plot_cache(
        self,
        sim_dir: Path,
        output_dir: Path,
        *,
        plot_mode: PlotMode,
        species: list[str] | None,
        t_start: float | None,
    ) -> bool:
        """Copy cached PNGs into output_dir when res.pickle and options are unchanged."""
        cache = self._plot_cache_path(
            sim_dir, plot_mode=plot_mode, species=species, t_start=t_start
        )
        if cache is None:
            return False
        output_dir.mkdir(parents=True, exist_ok=True)
        if plot_mode == "combined":
            if not cache.exists():
                return False
            shutil.copy2(cache, output_dir / "abundances.png")
            return True
        if plot_mode == "separate" and cache.is_dir():
            for png in cache.glob("*.png"):
                shutil.copy2(png, output_dir / png.name)
            return any(output_dir.glob("*.png"))
        if plot_mode == "both" and cache.is_dir():
            combined = cache / "abundances.png"
            if combined.exists():
                shutil.copy2(combined, output_dir / "abundances.png")
            for png in cache.glob("*.png"):
                if png.name == "abundances.png":
                    continue
                shutil.copy2(png, output_dir / png.name)
            return any(output_dir.glob("*.png"))
        return False

    def _save_plot_cache(
        self,
        sim_dir: Path,
        output_dir: Path,
        *,
        plot_mode: PlotMode,
        species: list[str] | None,
        t_start: float | None,
    ) -> None:
        cache = self._plot_cache_path(
            sim_dir, plot_mode=plot_mode, species=species, t_start=t_start
        )
        if cache is None:
            return
        if plot_mode == "combined":
            src = output_dir / "abundances.png"
            if src.exists():
                shutil.copy2(src, cache)
            return
        cache.mkdir(parents=True, exist_ok=True)
        for png in output_dir.glob("*.png"):
            shutil.copy2(png, cache / png.name)

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
        output_dir.mkdir(parents=True, exist_ok=True)

        from_cache = self._try_plot_cache(
            sim_dir, output_dir, plot_mode=plot_mode, species=species, t_start=t_start
        )
        completed: subprocess.CompletedProcess[str] | None = None
        if not from_cache:
            cmd = self.build_plot_command(
                sim_dir, output_dir, species=species, mode=plot_mode, t_start=t_start
            )
            completed = subprocess.run(
                cmd,
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=900,
                check=False,
            )
            if completed.returncode == 0:
                self._save_plot_cache(
                    sim_dir, output_dir, plot_mode=plot_mode, species=species, t_start=t_start
                )

        returncode = 0 if from_cache or (completed and completed.returncode == 0) else (
            completed.returncode if completed else 1
        )
        images = self._collect_images(run_id, output_dir, plot_mode) if returncode == 0 else []
        if include_images_base64 and images:
            images = attach_image_base64(images, output_dir)
        primary_url = images[0]["url"] if images else None

        return {
            "command": completed.args if completed else ["plot_cache"],
            "returncode": returncode,
            "stdout": completed.stdout if completed else "plot served from cache",
            "stderr": completed.stderr if completed else "",
            "run_id": run_id,
            "mode": plot_mode,
            "images": images,
            "image_url": primary_url,
            "plotted": species or self.settings.default_species.split(","),
            "from_cache": from_cache,
        }

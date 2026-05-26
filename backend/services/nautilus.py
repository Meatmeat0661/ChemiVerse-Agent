from __future__ import annotations

import subprocess
from pathlib import Path

from backend.config import NautilusSettings, ROOT
from backend.services.westlake_plot import WestlakePlotter


class NautilusRunner:
    def __init__(self, settings: NautilusSettings) -> None:
        self.settings = settings
        self.plotter = WestlakePlotter(settings)

    def tutorial_root(self) -> Path:
        root = self.settings.tutorial_root
        if not root.is_absolute():
            root = ROOT / root
        return root.resolve()

    def script_path(self) -> Path:
        script = Path(self.settings.script)
        if script.is_absolute():
            return script
        return (self.tutorial_root() / script).resolve()

    def simulation_dir(self, sim_dir: str | None) -> Path:
        name = sim_dir or self.settings.default_sim_dir
        path = Path(name)
        if not path.is_absolute():
            path = self.tutorial_root() / path
        return path.resolve()

    def build_command(
        self,
        sim_dir: str | None = None,
        use_evolution: bool = True,
        extra_args: list[str] | None = None,
    ) -> list[str]:
        directory = self.simulation_dir(sim_dir)
        cmd = [
            self.settings.python,
            str(self.script_path()),
            f"--dir={directory}",
        ]
        if use_evolution:
            cmd.append("--use_evolution")
        if extra_args:
            cmd.extend(extra_args)
        return cmd

    def run(
        self,
        sim_dir: str | None = None,
        use_evolution: bool = True,
        extra_args: list[str] | None = None,
        timeout: int | None = None,
    ) -> dict[str, object]:
        script = self.script_path()
        if not script.exists():
            raise FileNotFoundError(
                f"Westlake run script not found: {script}. "
                "Set nautilus.tutorial_root and nautilus.script in config.yaml."
            )

        directory = self.simulation_dir(sim_dir)
        if not directory.exists():
            raise FileNotFoundError(f"Simulation directory not found: {directory}")

        cmd = self.build_command(sim_dir, use_evolution, extra_args)
        completed = subprocess.run(
            cmd,
            cwd=str(self.tutorial_root()),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "command": cmd,
            "cwd": str(self.tutorial_root()),
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "sim_dir": str(directory),
            "pickle_path": str(directory / "res.pickle"),
        }

    def run_with_plot(
        self,
        sim_dir: str | None = None,
        use_evolution: bool = True,
        species: list[str] | None = None,
        plot_mode: str | None = None,
        include_images_base64: bool = False,
        extra_args: list[str] | None = None,
        timeout: int | None = None,
    ) -> dict[str, object]:
        run_id = self.plotter.new_run_id()
        sim_result = self.run(
            sim_dir=sim_dir,
            use_evolution=use_evolution,
            extra_args=extra_args,
            timeout=timeout,
        )
        sim_result["run_id"] = run_id

        if sim_result["returncode"] != 0:
            sim_result["plot"] = {
                "skipped": True,
                "reason": "simulation failed",
            }
            return sim_result

        pickle_path = Path(str(sim_result["pickle_path"]))
        if not pickle_path.exists():
            sim_result["plot"] = {
                "skipped": True,
                "reason": f"missing {pickle_path}",
            }
            return sim_result

        plot_result = self.plotter.plot(
            sim_dir=Path(str(sim_result["sim_dir"])),
            species=species,
            run_id=run_id,
            mode=plot_mode,  # type: ignore[arg-type]
            include_images_base64=include_images_base64,
        )
        sim_result["plot"] = plot_result
        return sim_result

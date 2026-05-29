from __future__ import annotations

import httpx


class RemoteSimulationClient:
    """Call a server that has westlake installed (visitors need not install westlake)."""

    def __init__(self, base_url: str, api_key: str = "", timeout: int = 3600) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def run(
        self,
        sim_dir: str | None = None,
        use_evolution: bool = True,
        plot: bool = True,
        plot_mode: str = "combined",
        species: list[str] | None = None,
    ) -> dict:
        body = {
            "sim_dir": sim_dir,
            "use_evolution": use_evolution,
            "plot": plot,
            "plot_mode": plot_mode,
            "species": species or [],
            "include_images_base64": True,
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/api/simulation/run",
                json=body,
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

    def plot_only(
        self,
        sim_dir: str | None = None,
        plot_mode: str = "combined",
        species: list[str] | None = None,
        *,
        include_explanations: bool = False,
        include_images_base64: bool = True,
    ) -> dict:
        """Plot from existing res.pickle. Explanations are separate (explain_plot)."""
        body = {
            "sim_dir": sim_dir,
            "plot_mode": plot_mode,
            "species": species or [],
            "include_images_base64": include_images_base64,
            "include_explanations": include_explanations,
        }
        with httpx.Client(timeout=600) as client:
            response = client.post(
                f"{self.base_url}/api/simulation/plot",
                json=body,
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

    def _explain_via_plot_endpoint(
        self,
        sim_dir: str | None,
        species: list[str] | None,
        *,
        plot_mode: str = "combined",
    ) -> dict:
        """Fallback when /plot/explain is missing on an older API build."""
        body = {
            "sim_dir": sim_dir or "example_simulation",
            "plot_mode": plot_mode,
            "species": species or [],
            "include_images_base64": False,
            "include_explanations": True,
        }
        with httpx.Client(timeout=90) as client:
            response = client.post(
                f"{self.base_url}/api/simulation/plot",
                json=body,
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()
        return {
            "explanations": data.get("explanations", {}),
            "explanation_llm_used": data.get("explanation_llm_used", False),
            "explanation_error": data.get("explanation_error"),
            "plot_stats": data.get("plot_stats"),
        }

    def explain_plot(
        self,
        sim_dir: str | None,
        species: list[str] | None,
        images: list[dict],
        *,
        plot_mode: str = "combined",
    ) -> dict:
        sim_dir = sim_dir or "example_simulation"
        body = {
            "sim_dir": sim_dir,
            "species": species or [],
            "images": images,
        }
        with httpx.Client(timeout=90) as client:
            response = client.post(
                f"{self.base_url}/api/simulation/plot/explain",
                json=body,
                headers=self._headers(),
            )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code != 404:
                    raise
                detail = ""
                try:
                    payload = exc.response.json()
                    detail = str(payload.get("detail", ""))
                except Exception:
                    detail = exc.response.text or ""
                if detail in ("Not Found", "404: Not Found") or (
                    "Not Found" in detail and "res.pickle" not in detail
                ):
                    return self._explain_via_plot_endpoint(
                        sim_dir, species, plot_mode=plot_mode
                    )
                raise
            return response.json()

    def get_conditions(self, sim_dir: str | None = None) -> dict:
        params = {}
        if sim_dir:
            params["sim_dir"] = sim_dir
        with httpx.Client(timeout=30) as client:
            response = client.get(
                f"{self.base_url}/api/simulation/conditions",
                params=params,
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

    def health(self) -> dict:
        with httpx.Client(timeout=30) as client:
            response = client.get(f"{self.base_url}/api/health")
            response.raise_for_status()
            return response.json()

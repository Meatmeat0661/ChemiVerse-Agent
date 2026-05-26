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
        plot_mode: str = "both",
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
        plot_mode: str = "both",
        species: list[str] | None = None,
    ) -> dict:
        body = {
            "sim_dir": sim_dir,
            "plot_mode": plot_mode,
            "species": species or [],
            "include_images_base64": True,
        }
        with httpx.Client(timeout=120) as client:
            response = client.post(
                f"{self.base_url}/api/simulation/plot",
                json=body,
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

    def health(self) -> dict:
        with httpx.Client(timeout=30) as client:
            response = client.get(f"{self.base_url}/api/health")
            response.raise_for_status()
            return response.json()

from __future__ import annotations

import base64
from pathlib import Path


def attach_image_base64(
    images: list[dict[str, str]],
    output_dir: Path,
) -> list[dict[str, str]]:
    enriched: list[dict[str, str]] = []
    for img in images:
        filename = img.get("filename") or ""
        path = output_dir / filename
        row = dict(img)
        row["path"] = str(path)
        if path.exists():
            row["base64"] = base64.b64encode(path.read_bytes()).decode("ascii")
        enriched.append(row)
    return enriched

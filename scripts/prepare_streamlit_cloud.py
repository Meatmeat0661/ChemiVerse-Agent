"""Copy ChemiVerse JSON into data/ for Streamlit Cloud deployment."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = Path(r"E:\大学\学术项目\Agent-ChemiVerse\数据库")
DST = ROOT / "data"

FILES = ("chemiverse_species.json", "chemiverse_reactions.json")


def main() -> None:
    DST.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        src = SRC / name
        dst = DST / name
        if not src.exists():
            raise SystemExit(f"Missing: {src}")
        shutil.copy2(src, dst)
        mb = dst.stat().st_size / 1024 / 1024
        print(f"OK {name} -> {dst} ({mb:.2f} MB)")
    print("\nNext:")
    print("  git add data/chemiverse_*.json")
    print("  git commit -m \"Add ChemiVerse database\"")
    print("  git push")


if __name__ == "__main__":
    main()

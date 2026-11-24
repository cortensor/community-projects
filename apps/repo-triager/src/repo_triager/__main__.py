"""Allow `python -m repo_triager …` as an alias of the console script."""

from __future__ import annotations

from repo_triager.cli import main

if __name__ == "__main__":
    raise SystemExit(main())

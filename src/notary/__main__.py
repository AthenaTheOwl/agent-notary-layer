"""Enable `python -m notary` by delegating to the CLI entry point."""

from __future__ import annotations

from notary.cli import main

if __name__ == "__main__":
    raise SystemExit(main())

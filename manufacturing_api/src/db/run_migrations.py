"""
Programmatic Alembic migration runner.

Allows running migrations without an alembic.ini by configuring the script location
to this package's migrations directory.

Usage examples:
    python -m src.db.run_migrations upgrade head
    python -m src.db.run_migrations downgrade -1
    python -m src.db.run_migrations history
"""

import sys
from pathlib import Path
from typing import List

from alembic import command
from alembic.config import Config


# PUBLIC_INTERFACE
def main(argv: List[str] | None = None) -> None:
    """Run Alembic command with programmatic configuration."""
    args = list(sys.argv[1:] if argv is None else argv)

    cfg = Config()
    # Script location is the migrations folder next to this file.
    here = Path(__file__).resolve()
    script_location = here.parent / "migrations"
    cfg.set_main_option("script_location", str(script_location))

    # Set DB URL for offline usage; env.py will override for online async usage.
    from src.db.config import get_settings

    settings = get_settings()
    cfg.set_main_option("sqlalchemy.url", settings.sync_database_url)

    if not args:
        print("No Alembic arguments provided. Example: upgrade head")
        sys.exit(1)

    # Dispatch to Alembic CLI command
    cmd = args[0]
    other = args[1:]

    if cmd == "upgrade":
        command.upgrade(cfg, *(other or ["head"]))
    elif cmd == "downgrade":
        command.downgrade(cfg, *(other or ["-1"]))
    elif cmd == "history":
        command.history(cfg, *other)
    elif cmd == "current":
        command.current(cfg, *other)
    elif cmd == "revision":
        command.revision(cfg, *other)
    elif cmd == "heads":
        command.heads(cfg, *other)
    elif cmd == "show":
        if not other:
            print("Usage: show <revision>")
            sys.exit(2)
        command.show(cfg, other[0])
    else:
        print(f"Unsupported Alembic command: {cmd}")
        sys.exit(2)


if __name__ == "__main__":
    main()

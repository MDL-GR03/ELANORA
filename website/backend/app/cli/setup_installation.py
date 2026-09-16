"""Prepare this installation's configuration, asking for nothing.

Guided setup runs this once. It generates any secret the installation needs
and leaves everything already configured untouched, so running it again is
safe. It prints which secrets it created, never their values.
"""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from app.core.secret_provisioning import provision_secrets

DEFAULT_ENV_FILE = Path("website/env/.env.prod")


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        type=Path,
        default=DEFAULT_ENV_FILE,
        help="Configuration file this installation reads",
    )
    return parser.parse_args()


def main() -> None:
    """Generate any missing secret for this installation."""
    arguments = _arguments()
    report = provision_secrets(arguments.env_file)
    print(json.dumps(asdict(report), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

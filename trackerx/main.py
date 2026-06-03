from __future__ import annotations

import sys
from pathlib import Path

# When run as a script or bundled by PyInstaller, ensure the package root
# is on sys.path so absolute imports like `from trackerx.app import ...` work.
if __package__ is None and __name__ == "__main__":
    package_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(package_root))

from trackerx.app import TrackerXApp


def main() -> int:
    app = TrackerXApp()
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())

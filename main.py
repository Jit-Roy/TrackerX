from __future__ import annotations

import sys
import ctypes
from pathlib import Path

# When run as a script or bundled by PyInstaller, ensure the package root
# is on sys.path so absolute imports like `from trackerx.app import ...` work.
if __package__ is None and __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import TrackerXApp


def main() -> int:
    if sys.platform == "win32":
        # Tell Windows this is a distinct app so the taskbar icon works properly
        try:
            myappid = "trackerx.desktop.app.2"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass
            
    app = TrackerXApp()
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())

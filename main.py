from __future__ import annotations

import sys
from app import TrackerXApp

def main() -> int:
    if sys.platform == "win32":
        # Tell Windows this is a distinct app so the taskbar icon works properly
        try:
            import ctypes
            myappid = "trackerx.desktop.app.1"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass
            
    app = TrackerXApp()
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())

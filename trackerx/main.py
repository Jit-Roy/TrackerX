from __future__ import annotations

from .app import TrackerXApp


def main() -> int:
    app = TrackerXApp()
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())

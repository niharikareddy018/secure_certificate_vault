"""
Deprecated entrypoint. The backend now lives under the `backend/` package.
This file forwards imports so existing commands keep working, but prefer:
  gunicorn backend.app:app
"""

import os
from backend.app import app  # noqa: F401

if __name__ == "__main__":
    from backend.app import app as _app
    port = int(os.getenv("PORT", "5000"))
    _app.run(host="0.0.0.0", port=port)
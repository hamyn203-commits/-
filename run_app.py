"""
Single-command launcher for the Pharmacy Management System.

It starts the FastAPI backend in a background thread, waits until it is ready,
then opens the desktop login window.
"""

from __future__ import annotations

import threading
import time
from typing import Optional

import requests
import uvicorn

from login_window import LoginWindow
from main import app


HOST = "0.0.0.0"
PORT = 8000
BASE_URL = f"http://127.0.0.1:{PORT}"


def start_backend() -> None:
    """Run the API server until the desktop process exits."""
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


def wait_for_backend(timeout_seconds: float = 10.0) -> Optional[str]:
    """Wait for the backend health endpoint and return an error if it fails."""
    deadline = time.monotonic() + timeout_seconds
    last_error: Optional[str] = None

    while time.monotonic() < deadline:
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=1)
            if response.status_code == 200:
                return None
            last_error = f"HTTP {response.status_code}"
        except requests.RequestException as exc:
            last_error = str(exc)
        time.sleep(0.25)

    return last_error or "Unknown startup error"


def main() -> None:
    server_thread = threading.Thread(target=start_backend, daemon=True)
    server_thread.start()

    startup_error = wait_for_backend()
    if startup_error:
        print(f"Warning: backend did not confirm readiness: {startup_error}")

    LoginWindow().run()


if __name__ == "__main__":
    main()

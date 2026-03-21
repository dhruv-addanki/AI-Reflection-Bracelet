from __future__ import annotations

import json
import os
import urllib.request


API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


def main() -> None:
    request = urllib.request.Request(
        f"{API_BASE_URL}/seed/demo",
        data=json.dumps({"reset": True}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        payload = json.loads(response.read().decode("utf-8"))
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

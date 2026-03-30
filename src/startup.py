"""Decode secrets from env vars into files on startup (for Railway)."""
import base64
import os

from src.config import DATA_DIR


def ensure_secrets():
    """Write secret files from env vars if they don't already exist on the volume."""
    secrets = {
        "SESSION_JSON_B64": os.path.join(DATA_DIR, "session.json"),
        "SERVICE_ACCOUNT_B64": os.path.join(DATA_DIR, "service_account.json"),
    }

    for env_var, file_path in secrets.items():
        encoded = os.environ.get(env_var, "")
        if not encoded:
            continue
        # Only write if the file doesn't exist yet (volume already has it)
        # or if FORCE_SECRET_UPDATE is set
        if os.path.exists(file_path) and not os.environ.get("FORCE_SECRET_UPDATE"):
            continue
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(base64.b64decode(encoded).decode("utf-8"))
        print(f"Wrote {file_path} from {env_var}")

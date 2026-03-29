import shutil
import os

from src.main import main

DATA_DIR = "/data"
SEED_FILES = ["session.json", "service_account.json"]


def seed_volume():
    """Copy seed files to the volume if they don't already exist."""
    if not os.path.isdir(DATA_DIR):
        return
    for filename in SEED_FILES:
        dest = os.path.join(DATA_DIR, filename)
        src = os.path.join("/app", filename)
        if not os.path.exists(dest) and os.path.exists(src):
            shutil.copy2(src, dest)
            print(f"Seeded {dest}")


if __name__ == "__main__":
    seed_volume()
    main()

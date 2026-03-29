import os

from src.main import main

DATA_DIR = "/data"

ENV_TO_FILE = {
    "SESSION_JSON": "session.json",
    "SERVICE_ACCOUNT_JSON": "service_account.json",
}


def seed_volume():
    """Write seed files from env vars to the volume if they don't already exist."""
    if not os.path.isdir(DATA_DIR):
        return

    for env_var, filename in ENV_TO_FILE.items():
        dest = os.path.join(DATA_DIR, filename)
        if not os.path.exists(dest):
            content = os.environ.get(env_var)
            if content:
                with open(dest, "w") as f:
                    f.write(content)
                print(f"Seeded {dest} from {env_var}")


if __name__ == "__main__":
    seed_volume()
    main()

"""
One-time setup script for Railway deployment.
Copies session.json and service_account.json to /data volume.

Run this locally with: railway run python setup_railway.py
(Make sure you have the Railway CLI installed and linked to your project)
"""
import shutil
import os
import sys

DATA_DIR = "/data"
FILES = ["session.json", "service_account.json"]


def main():
    if not os.path.isdir(DATA_DIR):
        print(f"ERROR: {DATA_DIR} not found. Are you running this on Railway?")
        print("Usage: railway run python setup_railway.py")
        sys.exit(1)

    for filename in FILES:
        if not os.path.exists(filename):
            print(f"WARNING: {filename} not found in current directory, skipping")
            continue
        dest = os.path.join(DATA_DIR, filename)
        shutil.copy2(filename, dest)
        print(f"Copied {filename} -> {dest}")

    print("\nDone! Your Railway volume now has the required files.")
    print("Redeploy or restart the service to pick them up.")


if __name__ == "__main__":
    main()

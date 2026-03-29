"""
One-time script: extracts and DECRYPTS Facebook cookies from your Chrome
and saves them to fb_cookies.json for the bot to use.

Usage:
  1. Close Chrome completely
  2. Run: python export_cookies.py
  3. Then run: python run.py

Re-run this script whenever the bot stops seeing private groups (session expired).
"""

import base64
import glob
import json
import os
import shutil
import sqlite3
import sys
import tempfile

import win32crypt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

CHROME_USER_DATA = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
CHROME_LOCAL_STATE = os.path.join(CHROME_USER_DATA, "Local State")
OUTPUT = "fb_cookies.json"


def get_chrome_key():
    """Get the AES key Chrome uses to encrypt cookies (Windows DPAPI)."""
    with open(CHROME_LOCAL_STATE, "r", encoding="utf-8") as f:
        local_state = json.load(f)
    encrypted_key_b64 = local_state["os_crypt"]["encrypted_key"]
    encrypted_key = base64.b64decode(encrypted_key_b64)
    encrypted_key = encrypted_key[5:]  # Remove "DPAPI" prefix
    return win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]


def decrypt_cookie_value(encrypted_value: bytes, key: bytes) -> str:
    """Decrypt a Chrome cookie value."""
    if not encrypted_value:
        return ""

    if encrypted_value[:3] in (b"v10", b"v20"):
        nonce = encrypted_value[3:15]
        ciphertext = encrypted_value[15:]
        aesgcm = AESGCM(key)
        try:
            return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")
        except Exception:
            return ""

    try:
        return win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)[1].decode("utf-8")
    except Exception:
        return ""


def find_all_cookie_dbs():
    """Find all Chrome profile cookie databases."""
    dbs = []
    # Check Default and all Profile N directories
    for profile_dir in ["Default"] + glob.glob(os.path.join(CHROME_USER_DATA, "Profile *")):
        if not os.path.isabs(profile_dir):
            profile_dir = os.path.join(CHROME_USER_DATA, profile_dir)
        for subpath in ["Network/Cookies", "Cookies"]:
            db = os.path.join(profile_dir, subpath)
            if os.path.exists(db):
                profile_name = os.path.basename(profile_dir)
                dbs.append((profile_name, db))
                break  # Only need one per profile
    return dbs


def extract_cookies_from_db(db_path: str, key: bytes) -> list[dict]:
    """Extract and decrypt Facebook cookies from a single DB."""
    tmp = tempfile.mktemp(suffix=".db")
    shutil.copy2(db_path, tmp)

    cookies = []
    try:
        conn = sqlite3.connect(tmp)
        cursor = conn.execute(
            "SELECT name, encrypted_value, host_key, path, is_secure, is_httponly "
            "FROM cookies WHERE host_key LIKE '%facebook.com'"
        )

        for name, encrypted_value, domain, path, secure, httponly in cursor.fetchall():
            value = decrypt_cookie_value(encrypted_value, key)
            if not value:
                continue
            cookies.append({
                "name": name,
                "value": value,
                "domain": domain,
                "path": path,
                "secure": bool(secure),
                "httpOnly": bool(httponly),
                "sameSite": "None" if secure else "Lax",
            })
        conn.close()
    finally:
        os.unlink(tmp)

    return cookies


def export():
    if not os.path.exists(CHROME_LOCAL_STATE):
        print("ERROR: Chrome Local State not found.")
        sys.exit(1)

    print("Extracting Chrome encryption key...")
    key = get_chrome_key()

    # Search all Chrome profiles for Facebook cookies
    dbs = find_all_cookie_dbs()
    if not dbs:
        print("ERROR: No Chrome cookie databases found.")
        sys.exit(1)

    print(f"Found {len(dbs)} Chrome profile(s)")

    # Try each profile, use the one with the most Facebook cookies
    best_cookies = []
    best_profile = ""

    for profile_name, db_path in dbs:
        print(f"  Checking {profile_name}...", end=" ")
        try:
            cookies = extract_cookies_from_db(db_path, key)
            cookie_names = {c["name"] for c in cookies}
            has_session = "c_user" in cookie_names and "xs" in cookie_names
            print(f"{len(cookies)} cookies" + (" (has FB session!)" if has_session else ""))

            if has_session and len(cookies) > len(best_cookies):
                best_cookies = cookies
                best_profile = profile_name
        except PermissionError:
            print("LOCKED — close Chrome first!")
            sys.exit(1)
        except Exception as e:
            print(f"error: {e}")

    if not best_cookies:
        print("\nERROR: No Facebook session found in any Chrome profile.")
        print("Make sure you are logged into Facebook in Chrome.")
        sys.exit(1)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(best_cookies, f, indent=2)

    print(f"\nExported {len(best_cookies)} cookies from '{best_profile}' to {OUTPUT}")
    for c in best_cookies:
        print(f"  {c['name']}: {'*' * min(len(c['value']), 10)}")
    print("\nYou can now run: python run.py")


if __name__ == "__main__":
    export()

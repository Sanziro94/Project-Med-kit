import os
import requests
import socket
import sys
import time
import getpass

hostname = socket.gethostname()
IPaddr   = socket.gethostbyname(hostname)
BASE_URL = os.environ.get("MEDKIT_SERVER", f"http://{IPaddr}:50000")

ADMIN_USERS = set(os.environ.get("ADMIN_USERS", "Sanziro").split(","))

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

def _prompt_credentials():
    user = input("Username: ").strip()
    password = getpass.getpass("Password: ")
    try:
        secret = input("Admin secret: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        sys.exit(1)
    return user, password, secret

def main():
    user, password, secret = _prompt_credentials()

    expected_password = ADMIN_PASSWORD or getpass.getpass("Set ADMIN_PASSWORD env var. Confirm password: ")

    if user not in ADMIN_USERS or password != expected_password:
        print("Access denied.")
        time.sleep(2)
        sys.exit(1)

    print(f"\nConnected to {BASE_URL}")

    while True:
        print("\n--- MENU ---")
        print("1. Ban an IP")
        print("2. Unban an IP")
        print("3. List banned IPs")
        print("4. Exit")

        try:
            choice = int(input("\nChoice: "))
        except (ValueError, EOFError):
            print("Please enter a number.")
            continue

        if choice == 1:
            ip = input("IP to ban: ").strip()
            try:
                r = requests.post(f"{BASE_URL}/ban-ip",
                                  json={"ip": ip, "secret": secret}, timeout=5)
                print(r.json())
            except requests.exceptions.RequestException as e:
                print(f"Error: {e}")

        elif choice == 2:
            ip = input("IP to unban: ").strip()
            try:
                r = requests.post(f"{BASE_URL}/unban-ip",
                                  json={"ip": ip, "secret": secret}, timeout=5)
                print(r.json())
            except requests.exceptions.RequestException as e:
                print(f"Error: {e}")

        elif choice == 3:
            try:
                r = requests.get(f"{BASE_URL}/banned-ips",
                                 params={"secret": secret}, timeout=5)
                data = r.json()
                banned = data.get("banned_ips", [])
                if banned:
                    for b in banned:
                        print(f"  • {b}")
                else:
                    print("  No IPs currently banned.")
            except requests.exceptions.RequestException as e:
                print(f"Error: {e}")

        elif choice == 4:
            print("Goodbye.")
            break

        else:
            print("Invalid choice.")

if __name__ == "__main__":
    main()

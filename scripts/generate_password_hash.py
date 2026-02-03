"""Script to generate password hashes for user setup"""

import sys
from app.core.security import get_password_hash

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.generate_password_hash <password>")
        sys.exit(1)
    
    password = sys.argv[1]
    hashed = get_password_hash(password)
    print(f"Password: {password}")
    print(f"Hash: {hashed}")
    print(f"\nUse this hash in your user database configuration.")

"""
Turns an account into an admin (permission level 2), so it can see
everyone's tasks. There's no endpoint for this on purpose, you have to
be on the machine to do it.

Make the account first (POST /users), then run:  python make_admin.py <username>
"""

import sys

import user_store

if len(sys.argv) != 2:
    sys.exit("usage: python make_admin.py <username>")

username = sys.argv[1]
if user_store.make_admin(username) is None:
    sys.exit(f"there's no user called {username}")

print(f"{username} is an admin now")

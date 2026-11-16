"""
Everything about users and logins lives in this file.

How users are laid out in Redis:

    user:<username>     one user, saved as JSON text
    session:<token>     the username that a login token belongs to

We never save a password. We save a hash of it, which is scrambled text
that can't be turned back into the password. To check a login we hash
what the person typed and see if it matches.
"""

import json
import secrets
import uuid

import bcrypt

import task_store

DEFAULT_PERMISSION = 0
ADMIN_PERMISSION = 2

# A login token stops working after a day.
SESSION_SECONDS = 24 * 60 * 60

# Hashing a password is slow on purpose, so somebody who steals the
# hashes can't try a billion guesses. A higher number is slower.
HASH_ROUNDS = 12


def user_key(username):
    return f"user:{username}"


def session_key(token):
    return f"session:{token}"


def create_user(username, password):
    """Saves a new user. Returns None if that username is already taken."""
    salt = bcrypt.gensalt(rounds=HASH_ROUNDS)
    user = {
        "id": str(uuid.uuid4()),
        "username": username,
        "password_hash": bcrypt.hashpw(password.encode(), salt).decode(),
        "permission_level": DEFAULT_PERMISSION,
    }
    # nx=True means "only save this if the key doesn't exist yet", so two
    # people can't grab the same username at the same moment.
    saved = task_store.redis_client.set(user_key(username), json.dumps(user), nx=True)
    if not saved:
        return None
    return user


def get_user(username):
    saved = task_store.redis_client.get(user_key(username))
    if saved is None:
        return None
    return json.loads(saved)


def check_login(username, password):
    """Returns the user if the password is right, or None if it isn't."""
    user = get_user(username)
    if user is None:
        return None
    if not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return None
    return user


def create_token(user):
    """Makes a long random token and remembers which user it belongs to."""
    token = secrets.token_urlsafe(32)
    task_store.redis_client.set(session_key(token), user["username"], ex=SESSION_SECONDS)
    return token


def get_user_for_token(token):
    """Returns the user a token belongs to, or None if it's wrong or expired."""
    username = task_store.redis_client.get(session_key(token))
    if username is None:
        return None
    return get_user(username)


def is_admin(user):
    return user["permission_level"] >= ADMIN_PERMISSION


def make_admin(username):
    """Turns an existing user into an admin. Returns None if there's no such user."""
    user = get_user(username)
    if user is None:
        return None
    user["permission_level"] = ADMIN_PERMISSION
    task_store.redis_client.set(user_key(username), json.dumps(user))
    return user


def public_user(user):
    """The parts of a user that are safe to send back (no password hash)."""
    return {
        "id": user["id"],
        "username": user["username"],
        "permission_level": user["permission_level"],
    }

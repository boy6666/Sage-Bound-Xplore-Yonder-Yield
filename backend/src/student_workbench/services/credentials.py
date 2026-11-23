from __future__ import annotations

import keyring

SERVICE_NAME = "student-workbench"


def key_for(connection_id: str) -> str:
    return f"platform:{connection_id}"


def save_password(connection_id: str, password: str) -> bool:
    try:
        keyring.set_password(SERVICE_NAME, key_for(connection_id), password)
    except Exception:
        return False
    return True


def delete_password(connection_id: str) -> bool:
    try:
        keyring.delete_password(SERVICE_NAME, key_for(connection_id))
    except Exception:
        return False
    return True

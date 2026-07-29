"""HTTP client helpers for the Streamlit frontend → FastAPI backend."""

from __future__ import annotations

import os
from typing import Any, Optional

import requests
import streamlit as st

DEFAULT_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")


def get_api_url() -> str:
    return st.session_state.get("api_url", DEFAULT_API_URL).rstrip("/")


def get_headers() -> dict[str, str]:
    headers = {"Accept": "application/json"}
    token = st.session_state.get("access_token")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def api_get(path: str, params: Optional[dict] = None) -> Any:
    url = f"{get_api_url()}/api/v1{path}"
    response = requests.get(url, headers=get_headers(), params=params, timeout=60)
    response.raise_for_status()
    return response.json()


def api_post(path: str, json: Optional[dict] = None, files=None, data=None) -> Any:
    url = f"{get_api_url()}/api/v1{path}"
    headers = get_headers()
    if files:
        headers.pop("Accept", None)
        response = requests.post(url, headers=headers, files=files, data=data, timeout=120)
    else:
        response = requests.post(url, headers=headers, json=json, timeout=120)
    response.raise_for_status()
    if response.status_code == 204:
        return None
    return response.json()


def api_patch(path: str, json: dict) -> Any:
    url = f"{get_api_url()}/api/v1{path}"
    response = requests.patch(url, headers=get_headers(), json=json, timeout=60)
    response.raise_for_status()
    return response.json()


def api_delete(path: str) -> None:
    url = f"{get_api_url()}/api/v1{path}"
    response = requests.delete(url, headers=get_headers(), timeout=60)
    response.raise_for_status()


def ensure_login(username: str, password: str) -> bool:
    url = f"{get_api_url()}/api/v1/auth/login"
    response = requests.post(
        url, json={"username": username, "password": password}, timeout=30
    )
    if response.status_code != 200:
        return False
    st.session_state["access_token"] = response.json()["access_token"]
    st.session_state["username"] = username
    return True

import os
import requests

PI_ZERO_API = "http://100.107.211.52:5050/api"

def display_image(image_path, source_type="direct", source_name=""):
    with open(image_path, "rb") as f:
        files = {"file": (os.path.basename(image_path), f, "image/png")}
        data = {"source_type": source_type, "source_name": source_name}

        resp = requests.post(f"{PI_ZERO_API}/display", files=files, data=data)

    if resp.status_code != 200:
        raise RuntimeError(f"API error {resp.status_code}: {resp.text}")

    return resp.text

def clear_display():
    resp = requests.post(f"{PI_ZERO_API}/clear")
    if resp.status_code != 200:
        raise RuntimeError(f"API error {resp.status_code}: {resp.text}")
    return resp.text

def undo_display():
    resp = requests.post(f"{PI_ZERO_API}/undo")
    if resp.status_code != 200:
        raise RuntimeError(f"API error {resp.status_code}: {resp.text}")
    return resp.text

def log_history():
    resp = requests.get(f"{PI_ZERO_API}/history")
    if resp.status_code != 200:
        raise RuntimeError(f"API error {resp.status_code}: {resp.text}")
    return resp.json()

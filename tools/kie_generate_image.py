"""Generate one image with Google Nano Banana via the kie.ai API.

Flow: createTask -> poll recordInfo -> download the first result URL.
Each successful run consumes kie.ai credits.

Usage:
    .venv/bin/python tools/kie_generate_image.py \
        --prompt-file .tmp/prompt.txt --out .tmp/raw.png \
        [--model nano-banana-pro] [--aspect 4:5] [--resolution 2K]

Requires KIE_API_KEY in .env (or the environment).
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

API_BASE = "https://api.kie.ai/api/v1/jobs"
POLL_INTERVAL_S = 5
TIMEOUT_S = 600


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def create_task(headers: dict, model: str, prompt: str, aspect: str, resolution: str) -> str:
    body = {
        "model": model,
        "input": {
            "prompt": prompt,
            "aspect_ratio": aspect,
            "resolution": resolution,
            "output_format": "png",
        },
    }
    r = requests.post(f"{API_BASE}/createTask", headers=headers, json=body, timeout=60)
    r.raise_for_status()
    data = r.json()
    if data.get("code") != 200 or not data.get("data", {}).get("taskId"):
        fail(f"createTask rejected: {data}")
    return data["data"]["taskId"]


def wait_for_result(headers: dict, task_id: str) -> str:
    deadline = time.time() + TIMEOUT_S
    while time.time() < deadline:
        r = requests.get(f"{API_BASE}/recordInfo", headers=headers, params={"taskId": task_id}, timeout=60)
        r.raise_for_status()
        info = r.json().get("data") or {}
        state = info.get("state")
        if state == "success":
            urls = json.loads(info.get("resultJson") or "{}").get("resultUrls") or []
            if not urls:
                fail(f"Task {task_id} succeeded but returned no image URLs: {info}")
            print(f"Done. Credits consumed: {info.get('creditsConsumed', 'unknown')}")
            return urls[0]
        if state == "fail":
            fail(f"Task {task_id} failed: {info.get('failCode')} {info.get('failMsg')}")
        print(f"  state={state} ...")
        time.sleep(POLL_INTERVAL_S)
    fail(f"Timed out after {TIMEOUT_S}s waiting for task {task_id} (it may still finish; do not resubmit blindly)")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--prompt-file", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--model", default="nano-banana-pro", choices=["nano-banana-pro", "nano-banana-2"])
    p.add_argument("--aspect", default="4:5")
    p.add_argument("--resolution", default="2K", choices=["1K", "2K", "4K"])
    args = p.parse_args()

    load_dotenv()
    api_key = os.getenv("KIE_API_KEY")
    if not api_key:
        fail("KIE_API_KEY is not set. Add it to .env in the project root.")
    prompt = args.prompt_file.read_text().strip()
    if not prompt:
        fail(f"Prompt file {args.prompt_file} is empty.")

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    task_id = create_task(headers, args.model, prompt, args.aspect, args.resolution)
    print(f"Task created: {task_id} (model={args.model}, aspect={args.aspect}, resolution={args.resolution})")

    url = wait_for_result(headers, task_id)
    img = requests.get(url, timeout=120)
    img.raise_for_status()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(img.content)
    print(f"Saved: {args.out}")


if __name__ == "__main__":
    main()

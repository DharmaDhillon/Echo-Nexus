"""
Echo Nexus CLI (v0.1)
Build and hash a dialogue block (later: push to storage).
"""
import json, hashlib
from pathlib import Path
from datetime import datetime, timezone

def sha3_hex(b: bytes) -> str:
    return hashlib.sha3_256(b).hexdigest()

def build_block(example_path="examples/sample_dialogue.json"):
    payload = json.loads(Path(example_path).read_text(encoding="utf-8"))
    payload.setdefault("timestamp_utc", datetime.now(timezone.utc).isoformat())
    jb = json.dumps(payload, ensure_ascii=False, separators=(",",":")).encode()
    payload["hash_self"] = sha3_hex(jb)
    return payload

if __name__ == "__main__":
    block = build_block()
    print(json.dumps(block, indent=2))

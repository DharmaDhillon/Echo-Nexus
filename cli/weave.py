"""
Echo Nexus CLI (v0.1)
Build + hash a dialogue block, score resonance, print result.
"""
import json, hashlib
from pathlib import Path
from datetime import datetime, timezone
from resonance.score import score_block

def sha3_hex(b: bytes) -> str:
    return hashlib.sha3_256(b).hexdigest()

def build_block(example_path="examples/sample_dialogue.json"):
    payload = json.loads(Path(example_path).read_text(encoding="utf-8"))
    payload.setdefault("timestamp_utc", datetime.now(timezone.utc).isoformat())
    jb = json.dumps(payload, ensure_ascii=False, separators=(",",":")).encode()
    payload["hash_self"] = sha3_hex(jb)
    return payload

def load_ethos(path="docs/manifesto.md") -> str:
    p = Path(path)
    return p.read_text(encoding="utf-8") if p.exists() else "Echo Nexus truth and resonance."

if __name__ == "__main__":
    block = build_block()
    ethos = load_ethos()
    scores = score_block(block, ethos)
    print(json.dumps({"scores": scores, "hash_self": block["hash_self"]}, indent=2))

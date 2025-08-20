"""
Echo Nexus CLI (v0.1)
Build + hash a dialogue block, quick-check alignment, score resonance, and (optionally) pin to IPFS.
"""

import json, hashlib, os, sys
from pathlib import Path
from datetime import datetime, timezone

# allow importing local package modules when run directly
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from resonance.score import score_block

# ------------------ utils ------------------
def sha3_hex(b: bytes) -> str:
    return hashlib.sha3_256(b).hexdigest()

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# ------------------ validation ------------------
REQUIRED_KEYS = ["v","dialogue_id","timestamp_utc","participants","content","hash_prev"]

def validate_payload(payload: dict) -> None:
    """Raise ValueError if the dialogue payload is malformed."""
    missing = [k for k in REQUIRED_KEYS if k not in payload]
    if missing:
        raise ValueError(f"Missing required keys: {missing}")
    if not isinstance(payload["participants"], list) or len(payload["participants"]) == 0:
        raise ValueError("participants must be a non-empty list")
    if not isinstance(payload["content"], list) or len(payload["content"]) == 0:
        raise ValueError("content must be a non-empty list")
    for turn in payload["content"]:
        if not isinstance(turn, dict) or "text" not in turn:
            raise ValueError("each content item must be an object with a 'text' field")

# ------------------ quick alignment gate ------------------
def quick_alignment(text: str, ethos: str, threshold: float = 0.80):
    """
    Lightweight alignment check using sentence-transformers.
    Returns (similarity: float|None, is_ok: bool).
    Falls back to allowing if model is unavailable.
    """
    try:
        from sentence_transformers import SentenceTransformer, util
        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        emb = model.encode([text, ethos], normalize_embeddings=True)
        sim = float(util.cos_sim(emb[0], emb[1]).cpu().numpy()[0][0])
        return sim, bool(sim >= threshold)
    except Exception:
        # If embeddings aren't available here, don't block—full scorer will still run.
        return None, True

# ------------------ IPFS pin ------------------
def pin_to_ipfs(obj_or_path):
    """
    Pins JSON payload (dict) or file path to IPFS.
    Returns CID string on success, or None if IPFS is not reachable.
    """
    try:
        import ipfshttpclient
        client = ipfshttpclient.connect()  # default /dns/localhost/tcp/5001/http
        if isinstance(obj_or_path, (str, Path)) and Path(obj_or_path).exists():
            res = client.add(str(obj_or_path))
            return res["Hash"]
        else:
            data = json.dumps(obj_or_path, ensure_ascii=False, separators=(",",":")).encode("utf-8")
            cid = client.add_bytes(data)
            return cid
    except Exception:
        return None

# ------------------ block build ------------------
def load_ethos(path="docs/manifesto.md") -> str:
    p = Path(path)
    return p.read_text(encoding="utf-8") if p.exists() else "Echo Nexus truth and resonance."

def build_block(example_path="examples/sample_dialogue.json"):
    payload = json.loads(Path(example_path).read_text(encoding="utf-8"))
    # ensure required fields
    payload.setdefault("timestamp_utc", utc_now_iso())
    payload.setdefault("hash_prev", "0x00")
    validate_payload(payload)

    # compute hash_self
    jb = json.dumps(payload, ensure_ascii=False, separators=(",",":")).encode()
    payload["hash_self"] = sha3_hex(jb)
    return payload

def dialogue_text(payload: dict) -> str:
    return " ".join([c.get("text","") for c in payload.get("content", [])])

# ------------------ main ------------------
if __name__ == "__main__":
    # 1) Build & validate payload
    block = build_block()

    # 2) Quick alignment gate (non-blocking; just an early signal)
    ethos = load_ethos()
    sim, ok = quick_alignment(dialogue_text(block), ethos, threshold=0.80)

    # 3) Full resonance scoring
    scores = score_block(block, ethos)

    # 4) Optional IPFS pin
    cid = pin_to_ipfs(block)

    # 5) Output combined result
    out = {
        "hash_self": block["hash_self"],
        "quick_alignment": {"similarity": sim, "ok": ok, "threshold": 0.80},
        "scores": scores,
        "ipfs_cid": cid
    }
    print(json.dumps(out, indent=2))

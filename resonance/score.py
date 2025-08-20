"""
Echo Nexus - Resonance Scoring Module (v0.1)
Computes resonance metrics for a dialogue block:
- Alignment (A): semantic similarity vs. ethos/manifesto
- Coherence (C): simple internal consistency proxy (length + spam penalty)
- Transparency (T): refs/URLs or explicit hints (stub upgradeable)
- Plurality (P): novelty/acknowledgement of dissent (stub upgradeable)
- Composite (R): weighted blend
"""

from __future__ import annotations
from typing import Dict, List
import re, json
import numpy as np

_EMB_MODELS = {}
_DEF_BACKENDS = [
    "sentence-transformers/all-MiniLM-L6-v2",
    "BAAI/bge-base-en-v1.5",
]

def _lazy_model(name: str):
    if name in _EMB_MODELS:
        return _EMB_MODELS[name]
    try:
        from sentence_transformers import SentenceTransformer
        m = SentenceTransformer(name)
        _EMB_MODELS[name] = m
        return m
    except Exception:
        _EMB_MODELS[name] = None
        return None

def _embed(text: str, model_name: str) -> np.ndarray:
    m = _lazy_model(model_name)
    if m is None:
        vec = np.zeros(512, dtype=np.float32)
        for token in re.findall(r"\w+", (text or "").lower()):
            vec[hash(token) % 512] += 1.0
        n = np.linalg.norm(vec) + 1e-9
        return vec / n
    return m.encode(text or "", normalize_embeddings=True)

def _cos_sim(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))

def _alignment(dialogue_text: str, ethos_text: str) -> float:
    scores = []
    for backend in _DEF_BACKENDS:
        try:
            v1 = _embed(dialogue_text, backend)
            v2 = _embed(ethos_text, backend)
            scores.append(_cos_sim(v1, v2))
        except Exception:
            continue
    return float(np.max(scores)) if scores else 0.0

def _degeneracy_penalty(text: str) -> float:
    lowered = (text or "").lower()
    banned = ["airdrop","token","buy now","casino","pump","dump"]
    repeats = sum(lowered.count(k) for k in banned)
    return max(0.0, 1.0 - 0.15 * repeats)

def _length_ok(turns: List[str]) -> float:
    if not turns: return 0.0
    avg = sum(min(300, len(t)) for t in turns) / (300.0 * len(turns))
    return float(min(1.0, max(0.1, avg)))

def _coherence(turns: List[str]) -> float:
    base = 0.6 * _length_ok(turns) + 0.4 * _degeneracy_penalty(" ".join(turns))
    return float(max(0.0, min(1.0, base)))

def _plurality_stub(text: str) -> float:
    has_dissent = bool(re.search(r"\b(dissent|counter|alternative|oppos|disagree)\b", (text or "").lower()))
    return 0.65 if has_dissent else 0.50

def _transparency_stub(block: Dict) -> float:
    text = " ".join(c.get("text","") for c in block.get("content", []))
    has_url = bool(re.search(r"https?://", text))
    has_refs = any(k in block for k in ("refs","references"))
    return 0.70 if (has_url or has_refs) else 0.50

def _composite(A: float, C: float, T: float, P: float) -> float:
    wA, wC, wT, wP = 0.35, 0.30, 0.20, 0.15
    return float(wA*A + wC*C + wT*T + wP*P)

def score_block(block: Dict, ethos_text: str) -> Dict[str, float]:
    turns = [c.get("text","") for c in block.get("content", [])]
    dialogue_text = " ".join(turns)
    A = _alignment(dialogue_text, ethos_text or "")
    C = _coherence(turns)
    T = float(block.get("transparency_hint", _transparency_stub(block)))
    P = float(block.get("plurality_hint", _plurality_stub(dialogue_text)))
    R = _composite(A, C, T, P)
    return {"A": round(A,4), "C": round(C,4), "T": round(T,4), "P": round(P,4), "R": round(R,4)}

if __name__ == "__main__":
    import pathlib
    sample = json.loads(pathlib.Path("examples/sample_dialogue.json").read_text(encoding="utf-8"))
    ethos = pathlib.Path("docs/manifesto.md").read_text(encoding="utf-8")
    print(json.dumps(score_block(sample, ethos), indent=2))

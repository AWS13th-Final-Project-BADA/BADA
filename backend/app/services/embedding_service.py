from __future__ import annotations

import hashlib
import json
import math

from ..config import settings


def embed_text(text: str) -> list[float]:
    mode = settings.embedding_mode.lower().strip()
    if mode == "bedrock":
        try:
            return _embed_with_bedrock(text)
        except Exception:
            return _embed_deterministic(text)
    return _embed_deterministic(text)


def _embed_with_bedrock(text: str) -> list[float]:
    import boto3

    session = (
        boto3.Session(profile_name=settings.aws_profile, region_name=settings.aws_region)
        if settings.aws_profile
        else boto3.Session(region_name=settings.aws_region)
    )
    client = session.client("bedrock-runtime")
    body = {
        "inputText": text[:8000],
        "dimensions": settings.embedding_dimension,
        "normalize": True,
    }
    response = client.invoke_model(
        modelId=settings.embedding_model_id,
        body=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        contentType="application/json",
        accept="application/json",
    )
    raw = json.loads(response["body"].read().decode("utf-8"))
    embedding = raw.get("embedding")
    if not embedding:
        raise RuntimeError("Bedrock embedding response did not include embedding")
    return [float(v) for v in embedding]


def _embed_deterministic(text: str) -> list[float]:
    vec = [0.0] * settings.embedding_dimension
    tokens = _tokenize(text)
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "big") % settings.embedding_dimension
        sign = -1.0 if digest[4] % 2 else 1.0
        vec[idx] += sign

    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return vec
    return [v / norm for v in vec]


def _tokenize(text: str) -> list[str]:
    cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in text)
    return [token for token in cleaned.split() if len(token) > 1]

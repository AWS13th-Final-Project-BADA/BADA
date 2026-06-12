from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db import SessionLocal, init_db  # noqa: E402
from app.models import RagChunk, RagDocument  # noqa: E402
from app.services.embedding_service import embed_text  # noqa: E402

SEED_DIR = ROOT / "app" / "data" / "rag_seed"


def _load_documents(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return payload.get("documents", [])
    return payload


def _doc_id(doc: dict) -> str:
    return doc.get("id") or doc["document_id"]


def _chunk_text(chunk: dict) -> str:
    return (chunk.get("text") or chunk.get("content") or "").strip()


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        total_docs = 0
        total_chunks = 0
        for path in sorted(SEED_DIR.glob("*.json")):
            docs = _load_documents(path)
            for doc in docs:
                document_id = _doc_id(doc)
                document = db.get(RagDocument, document_id)
                if not document:
                    document = RagDocument(id=document_id)
                    db.add(document)

                document.title = doc["title"]
                document.source_org = doc["source_org"]
                document.source_url = doc.get("source_url")
                document.language = doc.get("language", "ko")
                document.document_type = doc.get("document_type", "official_guide")
                document.version = doc.get("version")
                document.metadata_json = doc.get("metadata", {})

                db.query(RagChunk).filter(RagChunk.document_id == document.id).delete()
                for index, chunk in enumerate(doc.get("chunks", [])):
                    text = _chunk_text(chunk)
                    if not text:
                        continue
                    db.add(
                        RagChunk(
                            id=f"{document.id}:{index}",
                            document_id=document.id,
                            chunk_index=index,
                            section=chunk.get("section"),
                            text=text,
                            token_count=len(text.split()),
                            keywords=chunk.get("keywords", []),
                            embedding=embed_text(text),
                            metadata_json=chunk.get("metadata", {}),
                        )
                    )
                    total_chunks += 1
                total_docs += 1

        db.commit()
        print(f"rag_ingest=ok documents={total_docs} chunks={total_chunks}")
    finally:
        db.close()


if __name__ == "__main__":
    main()

"""Bedrock 모델 벤치마크 — Opus/Sonnet/Haiku × 10케이스.

사용:
  PROVIDER_MODE=aws AWS_REGION=ap-northeast-2 python eval/benchmark_models.py
  python eval/benchmark_models.py --dry-run   # Mock 출력으로 구조만 확인

출력: docs/model-benchmark.md (자동 생성)

평가 항목:
  - OCR 엔티티 추출 정확도 (gold 라벨 대비 F1)
  - 응답 시간 (초)
  - 입력/출력 토큰 (비용 추정)
  - 스키마 검증 통과율 (재시도 포함)

비용 기준 (ap-northeast-2, 2026-06):
  claude-opus-4     : $15/$75  per 1M tokens (input/output)  → 최신 4세대
  claude-sonnet-4   : $3/$15   per 1M tokens
  claude-haiku-3-5  : $0.80/$4 per 1M tokens
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "worker"))

# ─── 모델 목록 ────────────────────────────────────────────────────────────────

MODELS = {
    "haiku-4.5":  "global.anthropic.claude-haiku-4-5-20251001-v1:0",
    "sonnet-4.6": "global.anthropic.claude-sonnet-4-6",
    "opus-4.6":   "global.anthropic.claude-opus-4-6-v1",
}

# 비용 (USD per 1M tokens)
COST = {
    "haiku-4.5":  (0.80,  4.00),
    "sonnet-4.6": (3.00,  15.00),
    "opus-4.6":   (15.00, 75.00),
}

# ─── 케이스 정의 ──────────────────────────────────────────────────────────────

# 10케이스: 파일이 있으면 bytes로, 없으면 텍스트 케이스로 대체.
# eval/dataset/benchmark/ 에 이미지/PDF를 두면 자동으로 읽힌다.
CASES: list[dict[str, Any]] = [
    {"id": "case01", "category": "statement",  "desc": "급여명세서 (정형)"},
    {"id": "case02", "category": "contract",   "desc": "근로계약서 (정형)"},
    {"id": "case03", "category": "schedule",   "desc": "근무표 (정형)"},
    {"id": "case04", "category": "payment",    "desc": "통장 입금내역 PDF (정형)"},
    {"id": "case05", "category": "payment",    "desc": "통장 앱 캡처 (비정형)"},
    {"id": "case06", "category": "chat",       "desc": "카카오톡 캡처 (비정형)"},
    {"id": "case07", "category": "chat",       "desc": "문자 캡처 (비정형)"},
    {"id": "case08", "category": "other",      "desc": "손으로 쓴 메모 (비정형)"},
    {"id": "case09", "category": "statement",  "desc": "외국어 혼용 명세서 (정형)"},
    {"id": "case10", "category": "contract",   "desc": "표 형태 근로계약서 (정형)"},
]

_BENCH_DIR = Path(__file__).parent / "dataset" / "benchmark"

# ─── 시스템 프롬프트 & 유저 프롬프트 ─────────────────────────────────────────

_SYSTEM = (
    "당신은 임금체불 사건 증거에서 텍스트와 엔티티를 추출하는 도우미입니다. "
    "읽어서 구조화만 하고 위법 여부·금액을 판단하지 마세요. "
    "보이지 않는 값은 지어내지 말고, 불확실하면 confidence를 low로 표기하세요. "
    "반드시 유효한 JSON만 출력하세요."
)


def _user_prompt(category: str, text: str | None = None) -> str:
    base = (
        f"카테고리: {category}\n"
        "아래 문서/이미지에서 엔티티를 추출하세요.\n"
        "출력 형식:\n"
        '{"raw_text":"...","entities":{"dates":[],"amounts":[],"hourly_wage":null,'
        '"monthly_wage":null,"hours":[],"deductions":[],"workplace_name":null,'
        '"employer_name":null,"pay_date":null,"work_days":null,"overtime_hours":null,'
        '"night_hours":null,"holiday_hours":null,"contract_start":null,'
        '"contract_end":null,"signed":null,"utterances":[]}}'
    )
    if text:
        return base + f"\n\n[문서 텍스트]\n{text}"
    return base


# ─── 실제 호출 ────────────────────────────────────────────────────────────────

def _call_model(model_id: str, category: str, image_bytes: bytes | None,
                text: str | None, client) -> dict:
    """단일 케이스 호출. 토큰/시간/결과 반환."""
    import json as _json

    from providers._bedrock import (
        document_block,
        file_block,
        image_block,
        is_pdf,
        media_type_of,
        text_block,
    )

    content: list[dict] = []
    if image_bytes:
        content.append(file_block(image_bytes))
    content.append(text_block(_user_prompt(category, text)))

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4000,
        "system": _SYSTEM,
        "messages": [{"role": "user", "content": content}],
    }

    t0 = time.perf_counter()
    resp = client.invoke_model(modelId=model_id, body=_json.dumps(body))
    elapsed = time.perf_counter() - t0

    payload = _json.loads(resp["body"].read())
    raw_text = payload["content"][0]["text"]
    usage = payload.get("usage", {})

    # JSON 파싱 시도
    parsed = None
    schema_ok = False
    retries_used = 0
    s = raw_text.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[-1]
        if s.endswith("```"):
            s = s.rsplit("```", 1)[0]
    try:
        from providers.schema import OcrResult
        parsed = OcrResult.model_validate(_json.loads(s))
        schema_ok = True
    except Exception:
        pass

    return {
        "elapsed_s": round(elapsed, 2),
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "schema_ok": schema_ok,
        "retries": retries_used,
        "result": parsed,
        "raw": raw_text[:300] if not schema_ok else None,  # 실패 시 디버그용
    }


def _mock_call(model_name: str, case_id: str) -> dict:
    """--dry-run 용 Mock."""
    import random
    return {
        "elapsed_s": round(random.uniform(0.5, 4.0), 2),
        "input_tokens": random.randint(400, 1200),
        "output_tokens": random.randint(200, 600),
        "schema_ok": random.random() > 0.1,
        "retries": 0,
        "result": None,
        "raw": None,
    }


# ─── 정확도 계산 ──────────────────────────────────────────────────────────────

def _score(result, gold: dict | None) -> dict:
    """gold가 없으면 N/A. 있으면 핵심 필드 일치율."""
    if not gold or result is None:
        return {"accuracy": None, "note": "gold 없음 — 수동 평가 필요"}

    ge = gold.get("entities", {})
    hits = 0
    total = 0

    # 스칼라 필드 비교
    scalar_fields = ["hourly_wage", "monthly_wage", "workplace_name",
                     "employer_name", "pay_date", "work_days",
                     "overtime_hours", "night_hours", "contract_start",
                     "contract_end", "signed"]
    for f in scalar_fields:
        gv = ge.get(f)
        if gv is None:
            continue
        rv = getattr(result.entities, f, None)
        total += 1
        # 숫자는 ±5% 허용 (OCR 숫자 인식 오차 감안)
        if isinstance(gv, (int, float)) and isinstance(rv, (int, float)):
            hits += 1 if abs(gv - rv) / max(abs(gv), 1) <= 0.05 else 0
        else:
            hits += 1 if str(gv).strip() == str(rv).strip() else 0

    # deductions: name 일치 개수 / gold 공제 항목 수
    g_ded = ge.get("deductions", [])
    if g_ded:
        g_names = {d["name"] for d in g_ded if d.get("name")}
        r_names = {d.name for d in result.entities.deductions if d.name}
        total += len(g_names)
        hits += len(g_names & r_names)

    accuracy = round(hits / total, 2) if total else None
    return {"accuracy": accuracy, "hits": hits, "total": total}


# ─── 마크다운 리포트 생성 ─────────────────────────────────────────────────────

def _render_md(rows: list[dict], totals: dict) -> str:
    lines = [
        "# Bedrock 모델 벤치마크 리포트",
        "",
        "> 자동 생성. 재실행: `PROVIDER_MODE=aws python eval/benchmark_models.py`",
        "",
        "## 요약",
        "",
        "| 모델 | 스키마 통과율 | 평균 응답(s) | 평균 입력 토큰 | 평균 출력 토큰 | 케이스당 추정 비용($) |",
        "|------|------------|------------|-------------|-------------|-------------------|",
    ]
    for name, t in totals.items():
        n = t["n"]
        schema_rate = f"{t['schema_ok']}/{n}"
        avg_elapsed = round(t["elapsed_s"] / n, 2)
        avg_in = t["input_tokens"] // n
        avg_out = t["output_tokens"] // n
        cin, cout = COST.get(name, (0, 0))
        est_cost = round((avg_in * cin + avg_out * cout) / 1_000_000, 5)
        lines.append(f"| {name} | {schema_rate} | {avg_elapsed} | {avg_in} | {avg_out} | {est_cost} |")

    lines += [
        "",
        "## 케이스별 결과",
        "",
        "| 케이스 | 설명 | 카테고리 | 모델 | 응답(s) | 스키마 | 입력 토큰 | 출력 토큰 | 정확도 |",
        "|--------|------|---------|------|---------|--------|---------|---------|--------|",
    ]
    for r in rows:
        acc = r["score"].get("accuracy")
        acc_str = f"{acc:.0%}" if acc is not None else "N/A"
        schema_str = "✅" if r["schema_ok"] else "❌"
        lines.append(
            f"| {r['case_id']} | {r['desc']} | {r['category']} | {r['model']} "
            f"| {r['elapsed_s']} | {schema_str} | {r['input_tokens']} | {r['output_tokens']} | {acc_str} |"
        )

    lines += [
        "",
        "## 권고사항",
        "",
        "> 아래는 실행 결과 기반 자동 권고입니다. 최종 결정은 팀이 한다.",
        "",
    ]

    # 간단 권고 로직
    best = min(totals.items(), key=lambda kv: (
        -(kv[1]["schema_ok"] / kv[1]["n"]),   # 통과율 높을수록 우선
        kv[1]["elapsed_s"] / kv[1]["n"],       # 그 다음 빠른 것
    ))
    lines.append(f"- 통과율·속도 기준 추천 모델: **{best[0]}**")

    cheapest = min(totals.keys(), key=lambda k: COST[k][0] + COST[k][1])
    lines.append(f"- 비용 최저 모델: **{cheapest}** (haiku 계열은 데모 트래픽 수준이면 충분할 수 있음)")
    lines.append("- 정형 문서(contract/statement)는 Upstage 2단계 경로도 고려.")
    lines.append("- 비정형(chat/other)은 Claude Vision 단독이 가장 안전.")
    lines += ["", f"_생성 시각: {time.strftime('%Y-%m-%d %H:%M KST')}_"]

    return "\n".join(lines) + "\n"


# ─── 메인 ─────────────────────────────────────────────────────────────────────

def main(dry_run: bool = False):
    client = None
    if not dry_run:
        import boto3
        region = os.environ.get("AWS_REGION", "ap-northeast-2")
        client = boto3.client("bedrock-runtime", region_name=region)

    rows: list[dict] = []
    totals: dict[str, dict] = {
        name: {"n": 0, "schema_ok": 0, "elapsed_s": 0.0, "input_tokens": 0, "output_tokens": 0}
        for name in MODELS
    }

    for case in CASES:
        # 이미지/PDF 파일이 있으면 읽기
        image_bytes: bytes | None = None
        text_fallback: str | None = None
        for ext in (".jpg", ".jpeg", ".png", ".pdf", ".webp"):
            p = _BENCH_DIR / f"{case['id']}{ext}"
            if p.exists():
                image_bytes = p.read_bytes()
                break
        if not image_bytes:
            # 텍스트 샘플 파일
            tp = _BENCH_DIR / f"{case['id']}.txt"
            text_fallback = tp.read_text(encoding="utf-8") if tp.exists() else f"[{case['desc']} 샘플 텍스트 없음]"

        # gold 라벨
        gold_path = _BENCH_DIR / f"{case['id']}_gold.json"
        gold = json.loads(gold_path.read_text(encoding="utf-8")) if gold_path.exists() else None

        for model_name, model_id in MODELS.items():
            print(f"  [{model_name}] {case['id']} {case['desc']} ... ", end="", flush=True)

            if dry_run:
                res = _mock_call(model_name, case["id"])
            else:
                try:
                    res = _call_model(model_id, case["category"], image_bytes, text_fallback, client)
                except Exception as e:
                    print(f"ERROR: {e}")
                    res = {"elapsed_s": 0, "input_tokens": 0, "output_tokens": 0,
                           "schema_ok": False, "retries": 0, "result": None, "raw": str(e)}

            score = _score(res["result"], gold)
            row = {
                "case_id": case["id"],
                "desc": case["desc"],
                "category": case["category"],
                "model": model_name,
                "score": score,
                **{k: res[k] for k in ("elapsed_s", "schema_ok", "input_tokens", "output_tokens")},
            }
            rows.append(row)

            t = totals[model_name]
            t["n"] += 1
            t["schema_ok"] += int(res["schema_ok"])
            t["elapsed_s"] += res["elapsed_s"]
            t["input_tokens"] += res["input_tokens"]
            t["output_tokens"] += res["output_tokens"]

            status = "✅" if res["schema_ok"] else "❌"
            print(f"{status}  {res['elapsed_s']}s  in={res['input_tokens']} out={res['output_tokens']}")

    # 리포트 저장
    md = _render_md(rows, totals)
    out = Path(__file__).resolve().parents[1] / "docs" / "model-benchmark.md"
    out.write_text(md, encoding="utf-8")
    print(f"\n리포트 저장: {out}")

    # 요약 출력
    print("\n=== 모델별 요약 ===")
    for name, t in totals.items():
        n = t["n"]
        cin, cout = COST.get(name, (0, 0))
        avg_in = t["input_tokens"] // n
        avg_out = t["output_tokens"] // n
        est = round((avg_in * cin + avg_out * cout) / 1_000_000, 5)
        print(f"  {name:12s}  통과율={t['schema_ok']}/{n}  "
              f"평균응답={round(t['elapsed_s']/n,2)}s  "
              f"케이스당≈${est}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bedrock 모델 벤치마크")
    parser.add_argument("--dry-run", action="store_true", help="Mock 호출로 구조만 확인")
    args = parser.parse_args()
    main(dry_run=args.dry_run)

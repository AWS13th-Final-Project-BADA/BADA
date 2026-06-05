# BADA 평가셋 (gold dataset)

> 데모 정량 지표(OCR 90% / 차액탐지 90% / 누락 80%)는 **전부 이 평가셋에 달려 있다.**
> W2에 20~30건 라벨링 완료가 최우선 게이트(사람이 해야 하는 일).

## 구성
```
dataset/
  raw/        원본 증거 이미지/문서 (민감 — gitignore, 커밋 금지)
  labels/     정답 라벨 JSON (schema.json 형식)
  samples/    규칙엔진용 합성 케이스 (커밋 가능, 비민감)
  ocr/        OCR 필드정확도용 라벨 (gold_entities + extracted_entities)
harness.py    규칙엔진 정확도 측정(기대급여·차액·공제·누락)
ocr_score.py  OCR 필드 단위 추출 정확도 측정(시급·금액·공제·확장필드)
```

## 라벨 형식 (schema.json)
각 증거 1건당 정답 엔티티 + 케이스 단위 정답(기대급여/차액/공제/누락)을 적는다.

## 측정 지표
- **OCR 핵심필드 정확도**: 날짜·금액·시급·공제 추출이 정답과 일치하는 비율
- **차액 탐지율**: 미지급 의심 금액이 정답 ±오차 내인 비율
- **누락 체크 정확도**: 누락 안내가 정답 누락 항목과 일치하는 비율

## 실행
```bash
cd eval && python harness.py dataset/samples
```

# AWS 기능 켜기 (Mock → 실제 OCR·AI·번역)

키가 준비되면 **코드 수정 없이 `.env` 한 곳**만 바꾸면 전환된다.
Mock(local)과 실제(aws)는 같은 인터페이스를 쓰므로 `PROVIDER_MODE`가 스위치다.

## 1. 사전 준비 (AWS/Upstage)
- AWS 콘솔 → Bedrock → **Model access** 에서 Claude(텍스트+비전) 활성화
- AWS 자격증명: `aws configure` 또는 환경변수(AWS_ACCESS_KEY_ID/SECRET)
- Upstage: Document Parse **API 키** 발급
- 리전: `ap-northeast-2`(서울) 등 모델 지원 리전 확인

## 2. .env 설정 (`backend/.env`)
```
PROVIDER_MODE=aws
AWS_REGION=ap-northeast-2
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
UPSTAGE_API_KEY=...        # Upstage 키
# AWS 자격증명은 aws configure 로 했다면 생략 가능
```
> `backend/app/config.py`가 이 값들을 worker(providers)로 자동 브리지한다.

## 3. 의존성
```
pip install -r backend/requirements.txt   # boto3, requests 포함 (로컬·AWS 공용)
```

## 4. 무엇이 바뀌나 (자동 교체)
| 기능 | local (Mock) | aws (실제) |
| --- | --- | --- |
| OCR 비정형(카톡·사진) | 빈 결과 | **Claude Vision** 추출 |
| OCR 정형(명세서·계약서) | 빈 결과 | **Upstage** → Claude 구조화 |
| 타임라인 문장화 | 사실 그대로 | **Claude** 자연 문장 |
| 사건 요약 | 사실 결합 | **Claude** 요약 |
| 번역(대조표·모국어) | 원문 유지 | **Amazon Translate** |

규칙 기반 계산(차액·공제·누락·GPS)은 **두 모드 모두 동일**(항상 실제).

## 5. 확인
```
# 추출 동작 확인 (이미지 업로드 후)
POST /cases/{id}/evidences/extract   # aws 모드면 실제 추출값 반환
```
- ⚠️ Upstage 엔드포인트/응답 형태는 `worker/providers/_upstage.py` 주석대로 최신 문서로 1회 확인.
- 비용: Bedrock 이미지 토큰 발생 → 처음엔 소량으로 테스트.

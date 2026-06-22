# 통합 테스트 지침서

## E2E 분석 흐름 테스트

### 시나리오 1: 증거 업로드 → 동기 분석

```bash
# 1. 사건 생성
curl -X POST https://api.badasoft.com/cases \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"workplace_name":"테스트 사업장","agreed_hourly_wage":9860}'

# 2. 증거 업로드 (이미지)
curl -X POST https://api.badasoft.com/cases/<CASE_ID>/evidences/upload \
  -H "Authorization: Bearer <TOKEN>" \
  -F "category=statement" \
  -F "file=@sample_payslip.jpg"

# 3. 동기 분석 실행
curl -X POST https://api.badasoft.com/cases/<CASE_ID>/analyze \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{}'

# 4. 결과 확인
curl https://api.badasoft.com/cases/<CASE_ID>/analysis \
  -H "Authorization: Bearer <TOKEN>"
```

**확인:** `suspected_unpaid`, `timeline`, `deduction_items` 필드 존재

---

### 시나리오 2: SQS → Worker 비동기 분석

```bash
# SQS에 수동 메시지 전송
aws sqs send-message \
  --queue-url <SQS_URL> \
  --message-body '{"type":"analyze_case","case_id":"<CASE_ID>"}'

# Worker CloudWatch Logs 확인
aws logs tail /aws/ecs/bada-dev/worker --follow

# 결과 확인 (Case status = completed)
curl https://api.badasoft.com/cases/<CASE_ID> \
  -H "Authorization: Bearer <TOKEN>"
```

**확인:** `status: "completed"`, AnalysisResult DB 레코드 생성

---

### 시나리오 3: 음성 전사 (STT)

```bash
# 음성 파일 업로드 → SQS transcribe 메시지 발행
curl -X POST https://api.badasoft.com/cases/<CASE_ID>/evidences/upload \
  -H "Authorization: Bearer <TOKEN>" \
  -F "category=other" \
  -F "file=@sample_audio.mp3"

# Worker Logs에서 transcription 처리 확인
# Evidence.ocr_status = "done", ocr_text 확인
```

---

### 시나리오 4: Cognito 인증 E2E

```
1. 브라우저에서 https://badasoft.com 접속
2. "로그인" 클릭 → Cognito Hosted UI 리다이렉트
3. Google 계정으로 로그인
4. 콜백 → Access Token 수신 → 사건 목록 화면
5. API 호출 시 Bearer 토큰 검증 확인
```

---

### 시나리오 5: PDF Evidence Pack 생성

```bash
# 분석 완료된 사건에서 PDF 확인
aws s3 ls s3://bada-dev-report/packs/<CASE_ID>/ko/

# PDF 다운로드
aws s3 cp s3://bada-dev-report/packs/<CASE_ID>/ko/evidence-pack.pdf ./
```

**확인:** PDF 열림, 한국어 렌더링 정상, 면책 고지 포함

---

## 보안 테스트

```bash
# CORS 거부 확인 (허용되지 않은 오리진)
curl -H "Origin: https://evil.com" -I https://api.badasoft.com/health

# Rate limit 확인 (61번 연속 호출)
for i in $(seq 1 61); do curl -s -o /dev/null -w "%{http_code}\n" https://api.badasoft.com/health; done
# 마지막 요청이 429 반환

# 보안 헤더 확인
curl -I https://api.badasoft.com/health | grep -i "x-content-type\|strict-transport\|x-frame"
```

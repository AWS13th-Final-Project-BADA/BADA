# Transcribe 배포 트러블슈팅

> 음성 인식(STT) 기능을 ECS에 배포할 때 겪은 이슈와 해결 과정 기록.

---

## 이슈 1: Mock 텍스트만 나옴 (Transcribe 실제 호출 안 됨)

**증상**: 음성 파일 업로드 후 "읽은 원문 보기"에 고정 예시 텍스트만 표시됨.

**원인**: Secrets Manager에 `provider_mode=aws`가 없어서 ECS에서 `PROVIDER_MODE` 기본값 `"local"` → MockTranscriber 사용.

**해결**: Secrets Manager(`bada-dev/app-secrets`)에 `provider_mode: aws` 추가.

**교훈**: 로컬에서는 `.env`로 동작하지만, ECS에서는 Secrets Manager / Task Definition 환경변수에 명시적으로 넣어야 함.

---

## 이슈 2: Transcribe는 되는데 Claude 후처리(화자 분리)가 안 됨

**증상**: Transcribe 텍스트는 나오는데 전부 "Speaker 0:"으로만 표시. Claude 화자 분리 안 됨.

**원인 (복합적)**:

### 2-1. 환경변수 분리 미인지
- 인프라팀이 OCR(`PROVIDER_MODE`)과 Transcribe(`TRANSCRIBE_MODE`)를 독립 운영하기로 함
- ECS Task Definition: `PROVIDER_MODE=local`, `TRANSCRIBE_MODE=aws`
- 코드에서 `refine_transcript()`는 `PROVIDER_MODE`만 확인 → `"local"`이라 건너뜀

**해결**: `refine_transcript()`에서 `TRANSCRIBE_MODE` 환경변수를 참조하도록 수정.
```python
from config import TRANSCRIBE_MODE
if TRANSCRIBE_MODE != "aws":
    return raw_text
```

### 2-2. Deploy 워크플로우 paths 누락
- `deploy-dev.yml`의 `paths`에 `"worker/**"`가 없음
- `worker/services/transcription.py` 수정해도 **배포가 트리거 안 됨**
- GitHub Actions 성공해도 실제로는 이전 이미지로 돌고 있었음

**해결**: `workflow_dispatch`로 수동 트리거. 근본 해결은 `paths`에 `"worker/**"` 추가.

### 2-3. ECS Task 교체 안 됨
- Task Definition은 업데이트됐지만 기존 Task가 교체 안 됨 (rolling update 안 일어남)

**해결**: `aws ecs update-service --force-new-deployment` 실행.

---

## 이슈 3: Custom Vocabulary 생성 실패 (AccessDeniedException)

**증상**: CloudWatch 로그에 `transcribe:CreateVocabulary` 권한 없음 에러.

**원인**: ECS Task Role에 `transcribe:CreateVocabulary`, `transcribe:GetVocabulary` 권한 누락.

**해결**: IAM 정책에 해당 액션 추가 필요. (전사 자체는 동작 — Vocabulary 없이 진행됨)

---

## 이슈 4: S3에 파일이 안 올라옴 (대량 업로드 시)

**증상**: 35개 파일 업로드 시 S3에 안 올라감. 5개씩은 정상.

**원인**: 이전 배포에서 `STORAGE_MODE=local`이었거나, S3 버킷명이 잘못 설정된 상태에서 업로드됨 (ECS 컨테이너 로컬 디스크 → 재시작 시 소실).

**해결**: Secrets Manager에 올바른 `s3_bucket` 설정 확인. 재업로드.

---

## 체크리스트: ECS 배포 후 Transcribe가 동작하지 않을 때

1. **CloudWatch 로그 확인** — `/aws/ecs/bada-dev/backend`에서 에러 검색
2. **환경변수 확인** — `TRANSCRIBE_MODE=aws`가 Task Definition에 있는지
3. **Bedrock 승인** — 팀 계정에서 Anthropic Claude use case 제출 완료됐는지
4. **IAM 권한** — Task Role에 `transcribe:*`, `bedrock:InvokeModel` 있는지
5. **Deploy 트리거** — `worker/**` 변경 시 배포가 안 될 수 있음 (수동 트리거 필요)
6. **Task 교체** — force-new-deployment로 새 이미지 적용 확인
7. **S3 버킷** — 올바른 버킷명(`bada-dev-evidence`) 설정 확인

---

## 환경변수 정리 (ECS Task Definition 기준)

| 변수 | 값 | 역할 |
|------|-----|------|
| `PROVIDER_MODE` | `local` | OCR/LLM 전체 모드 (local=Mock) |
| `TRANSCRIBE_MODE` | `aws` | 음성 전사 독립 모드 (aws=실제 Transcribe+Claude) |
| `TRANSCRIPTION_DISPATCH_MODE` | `inline` | 전사 디스패치 (inline=Backend 직접, sqs=Worker 위임) |
| `S3_BUCKET` | `bada-dev-evidence` | 증거 파일 저장 버킷 |
| `AWS_REGION` | `ap-northeast-2` | AWS 서비스 리전 |

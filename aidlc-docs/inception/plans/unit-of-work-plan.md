# 유닛 분해 계획

## 계획 체크리스트

- [ ] 유닛 정의서 생성 (unit-of-work.md)
- [ ] 유닛 의존성 매트릭스 (unit-of-work-dependency.md)
- [ ] 유닛-요구사항 매핑 (unit-of-work-story-map.md)
- [ ] 유닛 경계 및 의존성 검증

---

## 예상 유닛 구성 (애플리케이션 설계 기반)

| 유닛 | 범위 | 우선순위 |
|------|------|----------|
| 1. 인프라 및 보안 | HTTPS, 보안 미들웨어, CORS, Worker 기동, Frontend ECS | P0 |
| 2. 인증 | Cognito JWKS 검증, 카카오/구글 소셜 로그인 | P0 |
| 3. Worker 파이프라인 | DB 직접 접근 전환, STT 구현, Bedrock 연동 | P0 |
| 4. PDF 생성 | WeasyPrint, 다국어 폰트, Evidence Pack | P1 |
| 5. Frontend (Next.js) | 전체 화면, 다국어, ECS 배포 | P1 |
| 6. PBT 및 품질 | Hypothesis, 규칙엔진 PBT, CI 통합 | P1 |

---

## 질문

## Question 1
유닛 실행 순서에 대해 — P0 유닛 3개를 어떻게 진행할까요?

A) 순차 실행 — 유닛 1(인프라) → 유닛 2(인증) → 유닛 3(Worker) 순서대로

B) 병렬 실행 — 유닛 1 완료 후, 유닛 2와 3을 동시에 진행

C) 최대 병렬 — 3개 모두 동시에 (의존성 충돌 가능성 있음)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 2
Worker 2단계 전환 시, 기존 Backend의 `/analyze` 동기 분석은?

A) 제거 — 모든 분석은 SQS → Worker 비동기로만 처리

B) 유지 — 간단한 분석은 동기, 복잡한(OCR+PDF)은 비동기 Worker

X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 3
Frontend(유닛 5)를 개발하는 동안 Backend의 기존 Static HTML은?

A) 그대로 유지 — Next.js 완성 전까지 기존 static 화면으로 서비스

B) 즉시 제거 — Frontend ECS 배포되면 static 경로 비활성화

X) Other (please describe after [Answer]: tag below)

[Answer]: B


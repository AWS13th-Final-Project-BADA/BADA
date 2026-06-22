# Requirements Verification Questions

BADA 프로젝트를 프로덕션 MVP 수준으로 완성하기 위해, 누락/미진 항목의 우선순위와 범위를 확인합니다.

---

## Question 1
MVP 배포 시 인증 방식은 어떻게 하시겠습니까? (현재 AUTH_MODE=demo로 인증 우회 상태)

A) Cognito + Google IdP 연동 완성 (인프라 이미 구축 완료, 백엔드 code 교환/JWT 검증만 구현)

B) 카카오/네이버/구글 소셜 로그인 (현재 OAuth 골격 존재) 유지 — Cognito 대신 직접 JWT

C) 데모/발표용이므로 현재 demo 모드 유지 (보안 없이 빠르게 배포)

D) Cognito + 소셜 로그인(카카오/구글) 모두 완성

X) Other (please describe after [Answer]: tag below)

[Answer]: D

---

## Question 2
Worker 분석 파이프라인의 MVP 범위는? (현재 consumer.py 완성, ECS desired=0)

A) 전체 파이프라인 활성화: OCR → 규칙분석 → 번역 → 타임라인 → 요약 → Worker ECS 기동

B) Backend 동기 분석만 유지 (현재 POST /analyze가 직접 수행) — Worker는 Phase 2로 연기

C) Worker 기동하되, analyze_case handler(Backend 경유)만 동작시키고 transcribe는 제외

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 3
HTTPS(SSL/TLS) 적용 범위는?

A) ACM 인증서 발급 + ALB HTTPS listener + HTTP→HTTPS 리다이렉트 (커스텀 도메인 있음)

B) ACM 인증서 + ALB HTTPS listener (ALB 기본 DNS 사용, 커스텀 도메인 없음)

C) MVP에서는 HTTP로 배포 (HTTPS는 추후)

X) Other (please describe after [Answer]: tag below)

[Answer]: X A로 할건데, 커스텀 도메인 아직 없음(구매예정)

---

## Question 4
프론트엔드 전략은? (현재 Backend가 서빙하는 Vanilla JS SPA 존재, Next.js 계획 있음)

A) 현재 Static HTML/JS를 개선·보완하여 MVP 출시 (빠름, 추가 인프라 불필요)

B) Next.js로 전환하여 별도 빌드/배포 (CloudFront + S3 또는 별도 ECS)

C) 현재 Static HTML을 그대로 사용 (UI 변경 없이 백엔드만 완성)

X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 5
PDF Evidence Pack 생성은 MVP에 포함합니까?

A) 포함 — 제출용(ko) PDF 1종 생성까지 완성 (WeasyPrint + 다국어 폰트)

B) 포함하되 HTML 리포트만 (/report.html) — PDF 파일 다운로드는 Phase 2

C) 제외 — 화면에서 결과 확인만 가능하면 됨

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 6
음성 전사(Speech-to-Text) 기능은 MVP에 포함합니까?

A) 포함 — Amazon Transcribe 연동하여 음성 증거 업로드 → 텍스트 변환

B) 제외 — 이미지/PDF 증거만 처리, 음성은 Phase 2

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 7
커뮤니티(게시판) 기능은 MVP에 포함합니까?

A) 포함 — 현재 구현된 게시판/댓글/번역/신고 그대로 배포

B) 제외 — 핵심 기능(증거→분석→결과)에 집중, 커뮤니티는 비활성화

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 8
카카오톡 봇 연동은 MVP에 포함합니까?

A) 포함 — 카카오 스킬 서버로 증거 업로드/GPS/분석 결과 조회 가능

B) 제외 — 웹 앱만 사용, 카카오 연동은 Phase 2

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 9
배포 일정은 언제까지 MVP를 AWS에 올리고 싶습니까?

A) 이번 주 내 (6/19~6/22) — 최소 기능만 빠르게

B) 다음 주 내 (6/23~6/29) — 핵심 기능 안정적으로

C) 7/10 최종 데모 전까지 — 시간 여유 있게 완성도 높여서

X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 10: Security Extensions
이 프로젝트에 보안 확장 규칙을 적용할까요?

A) Yes — 모든 SECURITY 규칙을 차단 제약으로 적용 (프로덕션 수준 권장)

B) No — SECURITY 규칙 건너뜀 (PoC, 프로토타입 프로젝트에 적합)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 11: Resiliency Extensions
이 프로젝트에 복원력 기준선을 적용할까요? (Well-Architected Reliability Pillar 기반 설계 가이드)

A) Yes — 복원력 기준선을 설계 시 방향 지침으로 적용 (비즈니스 크리티컬 워크로드 권장)

B) No — 복원력 기준선 건너뜀 (PoC, 프로토타입에 적합)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 12: Property-Based Testing
이 프로젝트에 속성 기반 테스트(PBT) 규칙을 적용할까요?

A) Yes — 모든 PBT 규칙을 차단 제약으로 적용 (비즈니스 로직, 데이터 변환이 있는 프로젝트 권장)

B) Partial — 순수 함수와 직렬화 round-trip에만 PBT 적용

C) No — PBT 규칙 건너뜀 (단순 CRUD, UI 전용 프로젝트에 적합)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

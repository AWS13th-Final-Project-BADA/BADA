# 애플리케이션 설계 계획

## 설계 범위

기존 BADA 시스템은 잘 구조화되어 있으므로(역공학 분석 완료), 이 단계에서는 **신규/미완성 컴포넌트**의 설계와 기존 컴포넌트 간 연동 설계에 집중합니다.

---

## 설계 체크리스트

- [ ] 컴포넌트 정의 (components.md)
- [ ] 컴포넌트 메서드 시그니처 (component-methods.md)
- [ ] 서비스 계층 정의 (services.md)
- [ ] 컴포넌트 의존성 관계 (component-dependency.md)
- [ ] 통합 설계 문서 (application-design.md)

---

## 설계 질문

### 컴포넌트 구성

## Question 1
Next.js 프론트엔드의 배포 방식은?

A) CloudFront + S3 (정적 내보내기, `next export`) — 가장 저렴, SSR 불가

B) 별도 ECS Fargate 태스크 (SSR 지원) — 비용 추가 (~$15/월), SEO 유리

C) Vercel 배포 (외부 서비스) — 간편하나 AWS 외부

X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 2
Next.js 프론트엔드와 Backend API 통신 방식은?

A) 프론트엔드가 ALB 도메인으로 직접 API 호출 (CORS 설정 필요)

B) Next.js API Routes를 프록시로 사용 (프론트 서버 → Backend, CORS 불필요)

C) CloudFront에서 `/api/*` 경로를 ALB로 오리진 라우팅 (단일 도메인)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 3
인증 토큰 관리 방식은? (Cognito + 소셜 로그인 후)

A) Cognito Access Token을 프론트에서 직접 사용 (Bearer 헤더) — Backend가 Cognito JWKS로 검증

B) Backend가 자체 JWT 발급 (소셜/Cognito 로그인 후 Backend JWT로 통일) — 현재 구조와 동일

C) HttpOnly 쿠키 기반 세션 (CSRF 보호 필요, 모바일 불편)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 4
Worker의 분석 실행 방식을 전환할까요? (현재: Worker가 Backend HTTP API를 호출하는 1단계 전략)

A) 1단계 유지 — Worker가 Backend `/analyze` 호출 (Worker에 DB 직접 연결 불필요, 단순)

B) 2단계 전환 — Worker가 DB 직접 접근하여 분석 수행 (Backend 경유 없음, 성능 향상)

X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 5
커스텀 도메인 구조는 어떻게 계획하고 있나요? (구매 예정이라고 하셨으므로)

A) 단일 도메인 — `bada.kr` (프론트 + API 모두 같은 도메인, 경로 분리: `/api/*`)

B) 서브도메인 분리 — `bada.kr`(프론트) + `api.bada.kr`(Backend)

C) 아직 미정 — 우선 ALB DNS로 배포하고 도메인은 나중에 결정

X) Other (please describe after [Answer]: tag below)

[Answer]: B


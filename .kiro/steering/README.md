# BADA — Kiro Steering 파일 세트

이 디렉토리는 BADA의 **AI-DLC Steering 규칙**이다.
Kiro / Amazon Q Developer가 코드·문안·인프라를 생성할 때 이 규칙들을 항상 참조하여,
팀이 합의한 설계 결정(스코프·안전·스택)을 AI가 자동으로 지키게 한다.

## 파일 구성

| 파일 | 역할 | inclusion |
| --- | --- | --- |
| `product.md` | 제품 정체성·포지셔닝·표현 정책(Guardrails)·면책·MVP 범위 | always |
| `tech.md` | 허용/금지 스택, OCR 라우팅, PDF 다국어, 번역 전략 | always |
| `architecture.md` | 규칙/LLM 분리 불변식, Pydantic 강제, 파이프라인, HITL | always |
| `domain.md` | DB 스키마, 엔티티, 공제 사전, 누락 규칙, GPS-lite | always |
| `security.md` | PII 마스킹(Upstage 한정), 암호화, 보존, PIPA | always |

모든 파일은 `inclusion: always`로 설정되어 매 생성 요청에 자동 주입된다.

## 핵심 불변식 (5개 파일을 관통하는 한 줄씩)

1. **판단하지 않는다** — "미지급 의심/확인 필요"만, "불법/확정/무조건" 금지. (product)
2. **AWS 관리형 단일 노선** — K8s·Kafka·OpenAI·Textract·ReportLab 금지. (tech)
3. **계산은 규칙, LLM은 문장화·OCR만** — 원본 숫자 무수정 보존. (architecture)
4. **GPS-lite** — 지오펜스 판정 + 카톡 교차검증까지만, 백그라운드 추적은 스트레치. (domain)
5. **외부 전송은 Upstage 하나** — 거기에만 PII 마스킹, Bedrock은 신뢰경계 내. (security)

## 사용법

1. 이 디렉토리(`.kiro/steering/`)를 리포 루트에 둔다.
2. Kiro가 자동 로드한다. (Q Developer는 Rules로 등록)
3. 설계 결정이 바뀌면 **코드보다 먼저 이 파일을 고친다** — 이게 AI-DLC의 핵심.
4. bolt 시작 전 Mob Elaboration에서 관련 steering을 함께 읽고 plan을 합의한다.

## AI가 self-validate 못 하는 게이트 (사람이 반드시 검증)

steering으로도 못 막는 5개. bolt 게이트에 사람을 배치:
① 평가셋 정답 라벨링 ② OCR 추출 정확도 판정 ③ 다국어 폰트 렌더 육안 확인
④ 면책·법률 표현 톤 검수 ⑤ GPS 교차검증 논리 타당성

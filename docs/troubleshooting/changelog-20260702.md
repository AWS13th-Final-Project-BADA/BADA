# 변경 이력 — 2026-07-02

> 작업: 모바일(mobile-native) 하드코딩 한국어 → i18n 전환 + 통화 표기 통일
> 브랜치: `feat/i18n-evidence-agent` (PR #228 머지, PR #229)

---

## 자료 업로드 "AI 증거 탐색" 다국어 전환 (PR #228)

### 문제
- 업로드 화면의 "AI 증거 탐색" 카드/알림/상태 문구가 한국어로 하드코딩되어 로케일을 바꿔도 번역되지 않음

### 수정
- `app/cases/upload.tsx`의 다음 문구를 `t()`로 전환
  - 카드 제목/본문, 스캔 완료 Alert(후보 O/X), 자동 등록·에이전트 업로드 상태, 갤러리 권한 오류 폴백
- `upload.agent.*` 키를 ko/en/vi/ja/km 5개 로케일에 추가
  - 건수 표기는 `{{scanned}}` · `{{candidates}}` · `{{uploaded}}` 보간

---

## 하드코딩 한국어 전면 i18n 스윕 (PR #229)

### 배경
- mobile-native 전체를 훑어 화면에 노출되는 하드코딩 한국어를 모두 `t()`로 전환

### 전환 대상

| 파일 | 전환 내용 |
|------|-----------|
| `app/_layout.tsx` | Stack 화면 타이틀 13종 |
| `app/index.tsx` | 인사말(`{{name}} 님`), 사용자 기본값 |
| `app/login.tsx` | 로그인 실패 알림, 이용약관/개인정보처리방침 |
| `app/cases/index.tsx` | 기간/임금 미입력, 통화 표기 |
| `app/cases/new.tsx` | 저장 실패 알림, 시급 placeholder |
| `app/cases/[id].tsx` | 사건/자료 삭제 확인 다이얼로그 |
| `app/cases/upload.tsx` | 사건 칩 라벨, 더보기/접기 |
| `app/cases/analysis.tsx` | 통화 표기, 파일명 폴백 |
| `app/gps.tsx` | 구역 확인, 일별 출근 요약, IN/OUT·시간, 최근 로그 |

### 신규 키 (ko/en/vi/ja/km)
- `common.user`, `common.won`, `home.greetingName`
- `login.failed` / `login.tokenError` / `login.terms` / `login.privacy`
- `cases.noPeriod` / `noWage` / `saveError` / `wagePlaceholder` / `shortLabel` / `deleteTitle` / `deleteBody` / `deleteEvidenceTitle` / `deleteEvidenceBody`
- `upload.showMore` / `upload.showLess`
- `analysis.fileIndex`
- `gps.checkArea` / `dailySummary` / `dayStat` / `dayInOut` / `recentLogs`

### 검증
- 5개 로케일 키 수 **376개 동일**(parity)
- `npm run check:i18n` 통과
- `npx tsc --noEmit` 통과(오류 0)

---

## 통화 표기 KRW(₩)로 통일 (PR #229)

### 원칙
- 이 서비스의 금액은 **항상 한국 원(KRW)** 이다. 로컬 통화(엔 `¥` / 동 `₫` / 리엘 `៛`)로 오해되면 안 된다.

### 수정
- `common.won` 표기를 로케일별로 정리
  - `ko`: `{{amount}}원`
  - `en` / `ja` / `vi` / `km`: `₩{{amount}}`
- 기존 `ja`는 `{{amount}}ウォン`(뜻은 맞으나 표기 불일치), `vi`/`km`는 `{{amount}} ₩`였던 것을 국제 표준 원화 기호 `₩` 접두 표기로 통일
- `₩`는 `¥`·`₫`·`៛`과 구별되어 어떤 언어에서도 "한국 원"으로 읽힘

---

## 범위 제외 / 후속 권장

- **소스 주석**의 한국어는 사용자 비노출이라 유지
- `src/features/community/types.ts`의 `COMMUNITY_CATEGORY_LABELS`, `src/features/cases/types.ts`의 `ISSUE_LABELS`는 **화면 표시 호출부가 없는 dead map**이라 이번 범위에서 제외
  - 후속 정리 권장: 맵 제거 또는 `t()` 기반 조회로 대체(호출부 신설 시)

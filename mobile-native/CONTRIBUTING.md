# BADA 모바일(mobile-native) 개발 규약

> 목적: **기능별 유지보수와 신규 개발이 서로 충돌 없이 병렬로** 진행되게 하는 규칙.
> 핵심 원리: 충돌은 "여러 사람이 같은 파일을 동시에 고칠 때" 생긴다. → **각자 자기 기능 폴더만 건드리게** 만든다.
> 상위 방향: `../aidlc-docs/construction/mobile/native-migration-plan.md` · 커밋/브랜치 공통 규칙: `../.kiro/steering/git.md`

---

## 1. 기능 모듈 경계 (가장 중요)

새 코드는 **기능별 폴더 안에** 둔다. 한 기능을 고칠 때 다른 기능 파일을 건드리지 않는다.

```
src/features/<기능>/
  api.ts          # 이 기능의 API 호출 (엔드포인트는 여기서만)
  types.ts        # 이 기능의 타입
  components/      # 이 기능 전용 컴포넌트
  hooks/          # 이 기능 전용 훅
  i18n/{ko,vi,en}.json   # 이 기능 문구(네임스페이스)
app/<기능 라우트>.tsx     # expo-router 화면 — features/<기능>을 import만
src/shared/        # 공용 transport·테마·UI (거의 안 바뀜 = 안정 구역)
```

> 현재 스캐폴드는 평면 구조(`src/lib`, `app/`)다. **이번에 강제 재배치는 하지 않는다.** 단,
> **신규 기능은 위 `features/<기능>` 규약을 따라 추가**하고, 기존 화면은 손볼 때 점진적으로 옮긴다.

### 기능 ↔ 담당(소유권) 매핑 *(GitHub 핸들은 팀에서 채울 것)*

| 기능 폴더 | 범위 | 담당(예시, `team-task-distribution.md` 기준) |
| --- | --- | --- |
| `features/auth` | 로그인/토큰/세션 | 프론트/인증 |
| `features/cases` | 사건 목록·생성·상세 | 프론트 |
| `features/evidence` | 카메라·파일 업로드 | 프론트 + OCR |
| `features/analysis` | 분석결과·타임라인·PDF | AI/분석 |
| `features/gps` | 백그라운드 위치·교차검증 | GPS 담당 |
| `features/community` | 게시판·댓글 | 커뮤니티 |
| `features/chat` | AI 상담 | Agent 담당 |
| `src/shared`, `app/_layout.tsx` | 공용·네비게이션 | **변경 시 리뷰 필수** |

---

## 2. 충돌 핫스팟 4곳과 회피 규칙

이 네 곳이 충돌의 90%다. 규칙을 지키면 거의 사라진다.

### ① 다국어 문구 (단일 JSON = 최악의 핫스팟)
- ❌ 모두가 `src/i18n/messages/ko.json` 하나를 수정 → 항상 충돌.
- ✅ **기능별 네임스페이스 JSON**으로 분리: `features/<기능>/i18n/ko.json`. 런타임에 합친다.
  ```ts
  // src/i18n/index.ts 가 각 기능 JSON을 namespace로 병합 (신규 기능은 한 줄 등록)
  i18n.store(require("@/features/cases/i18n/ko.json"), "ko", "cases");
  ```
- 한 기능 문구는 그 기능 JSON에서만 수정 → 서로 안 겹침.

### ② 네비게이션 (`app/_layout.tsx`)
- ❌ 화면 추가마다 중앙 `_layout.tsx`의 `Stack.Screen` 목록을 편집 → 충돌.
- ✅ **expo-router 파일기반**을 활용: 화면 파일만 추가하면 라우트가 생긴다. 제목 등은
  화면 파일 안에서 `export const options` 또는 기능별 중첩 `app/<기능>/_layout.tsx`로 둔다.
- 중앙 `_layout.tsx`는 **앱 전역 설정만** 두고 가급적 건드리지 않는다.

### ③ API (`src/lib/api.ts`)
- ✅ `lib/api.ts`는 **transport(토큰 주입·에러 처리)만** 두는 **안정 파일**. 새 엔드포인트를
  여기에 추가하지 않는다.
- ✅ 엔드포인트는 각 `features/<기능>/api.ts`에 둔다.
  ```ts
  // features/cases/api.ts
  import { fetchApi } from "@/lib/api";
  export const listCases = () => fetchApi<Case[]>("/cases");
  ```

### ④ `package.json` (의존성)
- ✅ 의존성 추가는 **그 작업만 담은 단독 PR**로. 다른 변경과 섞지 않는다.
- ✅ 버전 라인은 알파벳 순 유지(머지 충돌 최소화). lockfile은 한 PR에서만 갱신.

> `src/theme.ts`, `src/shared/**`도 준-핫스팟이다. **변경 시 PR 리뷰 필수**, 잦은 수정 금지.

---

## 3. 브랜치 전략

```
develop  ────────────────  (본체 — 모바일 작업은 직접 안 올림)
   └ feature/mobile-native  (모바일 통합 브랜치)
        ├ feature/mobile-auth
        ├ feature/mobile-cases
        ├ feature/mobile-gps
        └ feature/mobile-<기능>   ← 각 작업
```
- 작업은 항상 **`feature/mobile-<기능>`** 새 브랜치에서. (`git.md` 네이밍 준수)
- 베이스는 **`feature/mobile-native`**(모바일 통합). 본체 `develop`에는 통합 브랜치를 통해서만 반영.
- **자주 rebase**: 하루 1회 이상 `git pull --rebase origin feature/mobile-native`로 통합 브랜치를 따라간다(큰 충돌 예방).
- 한 PR = 한 기능. PR을 작게 유지.

---

## 4. 커밋 / PR 규약 (`git.md` 준수)

- 커밋: **한글**, `태그: 요약` (예: `기능: 사건 상세 화면 추가`). 태그 = 기능/수정/리팩터/문서/테스트/설정.
- PR 제목: 커밋과 동일. 본문: "무엇을/테스트 방법" 간략.
- PR 체크리스트:
  - [ ] 내 **기능 폴더 밖** 파일을 건드렸나? 건드렸다면 이유가 PR에 적혀 있나?
  - [ ] 문구는 기능 i18n JSON에만 추가했나?
  - [ ] 새 엔드포인트는 `features/<기능>/api.ts`에 있나?
  - [ ] **product.md 가드레일** 준수? (면책고지 노출, 금지표현 없음 — `t("disclaimer")`)
  - [ ] `npm run lint` + 타입체크 통과?

---

## 5. CODEOWNERS 템플릿

준비되면 `.github/CODEOWNERS`에 넣어 기능별 자동 리뷰어 지정(잘못된 영역 수정 시 리뷰 강제 → 충돌·사고 예방).

```
# mobile-native 기능별 소유자 (핸들은 실제 값으로 교체)
/mobile-native/src/features/auth/       @owner-auth
/mobile-native/src/features/cases/      @owner-frontend
/mobile-native/src/features/evidence/   @owner-frontend @owner-ocr
/mobile-native/src/features/analysis/   @owner-ai
/mobile-native/src/features/gps/        @owner-gps
/mobile-native/src/features/community/  @owner-community
/mobile-native/src/features/chat/       @owner-agent
# 공용/네비게이션은 변경 시 리드 리뷰
/mobile-native/src/shared/              @mobile-lead
/mobile-native/app/_layout.tsx          @mobile-lead
/mobile-native/package.json             @mobile-lead
```

---

## 6. 신규 기능 추가 절차 (복붙용)

```bash
# 1) 통합 브랜치에서 새 작업 브랜치
git switch feature/mobile-native && git pull --rebase
git switch -c feature/mobile-<기능>

# 2) 기능 폴더만 생성/수정
mkdir -p mobile-native/src/features/<기능>/{components,hooks,i18n}
#   - api.ts / types.ts / i18n/ko.json 등 작성
#   - 화면은 app/<라우트>.tsx 추가(파일만 추가 → 라우트 생성)

# 3) i18n 등록(한 줄)  — src/i18n/index.ts 에 namespace 추가

# 4) 검증 후 PR
npm run lint
git add mobile-native/src/features/<기능> app/<라우트>.tsx
git commit -m "기능: <기능> 화면 추가"
```

## 7. 충돌이 났을 때
- 대부분 핫스팟(①~④)에서 난다. 위 규칙으로 **사전 예방**이 1순위.
- 났다면: 통합 브랜치를 먼저 rebase로 흡수 → 내 기능 파일은 거의 안 겹치므로 충돌 지점이 좁다.
- i18n/네비게이션 충돌이 잦으면 → 해당 기능을 §2 규칙대로 분리했는지 점검.

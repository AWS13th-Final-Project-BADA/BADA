# BADA Frontend (Next.js + next-intl)

W1 bolt에서 초기화:
```bash
npx create-next-app@latest . --ts --app --tailwind
npm i next-intl
```

## 구조 (structure.md)
```
app/          App Router 페이지 (로그인/사건/업로드/결과/타임라인/GPS지도)
components/    재사용 컴포넌트 (TimelineView, UploadDropzone, ResultCard ...)
locales/       ko/vi/en(완성) + km/ne/id(골격)
lib/           api 클라이언트, i18n 설정
```

## 화면 (MVP)
1. 로그인 (모국어 선택 → UI 즉시 전환)
2. 사건 생성 (사업장·사업주·근무기간·시급·주당시간·문제유형)
3. 증거 업로드 (카테고리 태그 + S3 presigned 직접 업로드)
4. 결과 (타임라인·비교/공제표·대조표·누락 — `확인 필요` 배지)
5. GPS 지도뷰 (IN_WORKPLACE/OUTSIDE + 교차검증 표시)
6. 다운로드 (제출용 ko PDF / 이해용 모국어)

## 원칙
- 모든 "이해용" 화면은 모국어. 원문은 항상 병기.
- 결과 화면 상단에 면책 고지 노출(product.md).

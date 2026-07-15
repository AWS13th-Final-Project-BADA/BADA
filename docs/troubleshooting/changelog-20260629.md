# 변경 이력 — 2026-06-29 (기능 검증 및 UI 고도화)

> 작업자: 김재현
> 브랜치: `feature/translation`, `fix/upload-progress-indicator`, `fix/case-detail-label`, `feature/notifications`, `fix/waf-upload-block`, `fix/rate_limit`

---

## 다국어 지원 (feature/translation)

- 로그인 화면 언어 전환 드롭다운 연결 (i18n-js)
- LocaleProvider Context 적용 — 언어 변경 시 전체 앱 리렌더링
- AsyncStorage 영속성 — 앱 재시작해도 이전 선택 언어 유지
- 전체 화면 하드코딩 한국어 → `t()` 전환 (홈/사건/업로드/분석/채팅/커뮤니티/GPS)
- 크메르어(km) + 일본어(ja) 번역 파일 추가 → 5개 언어 지원
- 커뮤니티 게시글 자동 번역 (locale != ko일 때 `/community/translate` API 호출)
- 하단 네비게이션 라벨 다국어 적용

## 업로드 UX 개선 (fix/upload-progress-indicator)

- 파일 업로드 중 풀스크린 오버레이 (스피너 + "업로드 중..." 텍스트)
- 업로드 완료 후 "분석 보러가기" 버튼 표시
- 음성 파일 선택 버튼 추가 (STT 연동용)

## 분석 결과 화면 개선 (fix/case-detail-label)

- "분석 결과" 버튼명 → "자료 업로드 이력"으로 변경
- 분석 페이지 대제목 "자료 업로드 이력", 소제목 "사전 분석 결과"
- 분석 미완료 시 더미 데이터 제거 → 상태별 분기:
  - 증거 0건: "자료 업로드 필요"
  - 증거 있음 + 분석 안 함: "자료 분석이 준비되었습니다"
  - 409 (재실행 필요): "다시 분석"
- 분석 미완료 상태에서 업로드된 증거 리스트 표시
- "자료 보충하기" 버튼 추가 (업로드 화면 바로 이동)
- 분석 완료 시 스크롤 맨 위로 자동 이동
- 요약 텍스트 문단 분리 (가독성 개선)
- 분석 결과 로딩 중 풀스크린 오버레이

## 홈 화면 개선

- "자료 업로드" 퀵카드 제거 (사건 미선택 상태 문제)
- 퀵카드를 카드형 리스트(1열)로 변경: 내 사건 목록 + AI 챗봇에게 물어보기
- "다음에 할 일" 하드코딩 섹션 제거
- 커뮤니티 섹션 목업 → 실제 API 연동 (최신 3개 글)
- 사용자 이름 표시 복원

## 하단 네비게이션 재설계

- 탭 순서: 홈 / 커뮤니티 / + / 챗봇 / 설정
- + 버튼: 팝업 메뉴 (새 사건 만들기 / 사건 선택)
- 설정 화면 신규: 프로필, 언어 선택, GPS 기록, 카카오 연동, 로그아웃

## 로그인 화면

- 소셜 로그인 아이콘: 외부 URL → 로컬 이미지 교체 (Google/Kakao/Naver)

## 알림 기능 (feature/notifications)

- Backend: Notification 모델 + API (목록/읽음/전체읽음/미읽음수)
- Alembic 마이그레이션: `notifications` 테이블 생성
- 이벤트 연동: 분석 완료 → 알림, 내 게시글에 댓글 → 알림
- Frontend: 알림 화면 (읽음/미읽음 구분, 클릭 시 사건 이동)
- TopBar 종 아이콘 → 알림 화면 연결

## 인프라/운영

- WAF `SizeRestrictions_BODY` 규칙 → Count 모드 전환 (파일 업로드 403 해결)
- Rate Limit 상향 (모바일 앱 사용 패턴 대응)
- ECS 마이그레이션 직접 실행 (alembic upgrade head via ECS Exec)

---

## 발견된 이슈 및 메모

| 이슈 | 상태 | 비고 |
|------|------|------|
| WAF 파일 업로드 차단 | 해결됨 | terraform apply 완료 |
| Rate Limit 60/min 부족 | 해결됨 | 상향 + 재배포 |
| 분석 API 409 (report 포맷 불일치) | FE 대응 완료 | 이전 분석 결과는 재실행 필요 |
| ECS 배포 실패 (notifications 테이블 미존재) | 해결됨 | alembic 마이그레이션 + 재배포 |

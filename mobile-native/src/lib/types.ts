/**
 * 타입 배럴(barrel) — 기능별 타입 파일을 한 곳에서 재export.
 *
 * ⚠️ 이 파일에는 타입을 "직접 정의하지 않는다". 실제 정의는 각 기능 폴더에 둔다:
 *   - 공유 primitives : @/shared/types
 *   - 사건           : @/features/cases/types
 *   - 증거           : @/features/evidence/types
 *   - 분석           : @/features/analysis/types
 *   - 커뮤니티        : @/features/community/types
 *   - 챗봇           : @/features/chat/types
 *
 * 신규 기능 타입은 해당 기능 폴더에 추가하고, 필요하면 여기 한 줄만 더한다.
 * (기존 `@/lib/types` import 호환을 위해 유지)
 */
export * from "@/shared/types";
export * from "@/features/cases/types";
export * from "@/features/evidence/types";
export * from "@/features/analysis/types";
export * from "@/features/community/types";
export * from "@/features/chat/types";

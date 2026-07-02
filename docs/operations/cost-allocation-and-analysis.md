# BADA 비용 할당 태그 & 비용 분석 (B-4)

> 목적: 리소스 비용을 태그 기준으로 분해·분석할 수 있게 하고, Cost Explorer 분석
> 절차와 캡처 체크리스트를 제공한다.
> 관련: `infra/providers.tf`(default_tags), `infra/main.tf`(common_tags), AWS Budgets($1,000 경보)

## 1. 태그 체계

모든 리소스는 아래 비용 할당 태그를 갖는다. `infra/providers.tf`의 `default_tags`가
catch-all로 부착하고, 개별 리소스는 `merge(local.common_tags, {...})`로 동일 값을 유지한다.

| 태그 키 | 값(dev) | 용도 |
|---|---|---|
| `Project` | `bada` | 프로젝트 단위 비용 집계 |
| `Environment` | `dev` | 환경(dev/prod) 분리 |
| `ManagedBy` | `terraform` | IaC 관리 리소스 식별 |

> Terraform provider(AWS 5.x) `default_tags`는 개별 리소스가 같은 키를 동일 값으로
> 설정한 경우 plan 변화를 만들지 않는다. 따라서 이번 도입은 태그 누락 리소스만 보강한다.

## 2. 비용 할당 태그 활성화 (수동 — Billing 콘솔)

> ⚠️ 태그를 Cost Explorer/CUR의 **비용 분해 기준**으로 쓰려면 결제(관리) 계정의
> Billing 콘솔에서 "비용 할당 태그"로 **활성화**해야 한다. 이 단계는 Terraform으로
> 관리되지 않으며, 활성화 후 데이터 반영에 최대 24시간이 걸린다.

절차:
1. AWS 결제(관리) 계정 → **Billing and Cost Management → Cost allocation tags**
2. **User-defined cost allocation tags** 목록에서 `Project`, `Environment` 선택
3. **Activate** 클릭
4. 활성화 후 Cost Explorer에서 해당 태그를 그룹화 기준으로 사용 가능(반영까지 최대 24h)

> 공용 계정이라 결제 콘솔 접근 권한이 인프라 담당자/계정 관리자에 한정될 수 있다.
> 권한이 없으면 활성화는 계정 관리자에게 요청한다.

## 3. Cost Explorer 분석 절차

1. **Cost Explorer** → 기간: 프로젝트 시작(6/19)~현재
2. **Group by → Tag → `Project`** (또는 `Environment`) 로 분해
3. **Group by → Service** 로 서비스별(ECS/RDS/S3/Bedrock 등) 비용 확인
4. **Filter**: `Project = bada` 로 한정
5. 일별 추이(Daily)로 Auto Scaling/부하 테스트 시점의 비용 스파이크 확인

권장 캡처(포트폴리오/발표용):
- [ ] Service별 누적 비용 (파이/막대)
- [ ] 일별 비용 추이 (부하 테스트일 스파이크 포함)
- [ ] `Project=bada` 태그 필터 적용 화면
- [ ] AWS Budgets 대비 실제 사용($1,500 상한 / $1,000 경보 대비)

## 4. AWS Budgets 연계 (기존)

- 팀 예산 추적 Budget이 이미 존재(`implementation-status.md` 참조), 임계 $1,000 경보.
- Cost Explorer 분석과 Budgets 경보를 함께 캡처하면 "비용 가시성 + 통제" 스토리 완성.

## 5. 종료(7/10) 연동

- 태그/`default_tags`는 비용 발생 리소스가 아니므로 정리 대상 아님(코드에 잔존해도 무해).
- 종료 후 최종 Cost Explorer 스냅샷(총사용액/서비스별)을 1회 캡처해 산출물로 보존.

## 6. 남은 향상 여지 (보류)

- `Component`/`Service` 태그(Backend/Worker/RDS 등) 추가 시 컴포넌트 단위 분해 가능.
  현재는 AWS **Service** 차원으로도 충분히 분해되므로 종료 기간 대비 보류.
- CUR(Cost and Usage Report) + Athena 분석은 dev/데모 규모 대비 과함 → 보류.

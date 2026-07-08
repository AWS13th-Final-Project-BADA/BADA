#!/usr/bin/env python3
"""BADA Worker Auto Scaling 실증용 SQS 적체 생성기 (#9-b)

목적: 분석 큐(bada-dev-analysis)에 메시지를 대량 투입해 SQS backlog를 만들고,
      Worker의 backlog-per-task Target Tracking(#4, 목표 5msg/task)이 desired_count를
      1 -> 2 -> 3으로 올리는 것을 유발한다. (BADA의 실제 서지 시나리오: 다수 사용자가
      동시에 분석 요청 -> 큐 적체 -> Worker scale-out)

비용 0의 원리: analyze_case 핸들러는 case_id로 DB를 먼저 SELECT하는데, 존재하지 않는
      case_id를 주면 "case not found"로 **첫 DB 조회에서 실패** -> Bedrock/OCR 미호출.
      실패한 메시지는 삭제되지 않고 visibility timeout(900s) 동안 in-flight 상태가 되며,
      테스트 창(수 분) 안에는 DLQ로 가지 않는다(maxReceiveCount=5 x 15분 = 75분 소요).

⚠️ 주의
 - 공용 데모 환경. 팀 공지 + 데모/리허설 시간 회피.
 - Worker 실패 메트릭(worker_sqs_messages_total{status=failed})이 합성적으로 튄다(정상).
 - 테스트 후 --purge 로 큐를 비워 잔여 메시지가 재출현/ DLQ로 가는 것을 막는다.
   (purge는 큐의 모든 메시지를 지우므로, 실제 트래픽이 없는 창에서만 실행)

사용:
  # 자격증명: bada-team 프로파일
  set AWS_PROFILE=bada-team   (PowerShell: $env:AWS_PROFILE="bada-team")

  # 6000건 투입 (기본) -> Worker 스케일아웃 유발
  python load-test/sqs/fill_backlog.py --count 6000

  # 스케일 확인
  aws application-autoscaling describe-scaling-activities --service-namespace ecs \
    --region ap-northeast-2 --profile bada-team \
    --resource-id service/bada-dev-cluster/bada-dev-worker --output table

  # 6000건 투입 + 드레인 곡선(큐 age/소진) 관측
  python load-test/sqs/fill_backlog.py --count 6000 --watch

  # 정리 (테스트 종료 후)
  python load-test/sqs/fill_backlog.py --purge

필요: boto3 (pip install boto3), AWS 자격증명(AWS_PROFILE 또는 기본 체인).
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import sys
import time
import uuid

try:
    import boto3
except ImportError:
    sys.exit("boto3가 필요합니다: pip install boto3")

DEFAULT_QUEUE = "bada-dev-analysis"
DEFAULT_REGION = "ap-northeast-2"


def resolve_queue_url(sqs, queue: str) -> str:
    if queue.startswith("https://"):
        return queue
    return sqs.get_queue_url(QueueName=queue)["QueueUrl"]


def make_entries(n: int, start_idx: int) -> list[dict]:
    """analyze_case 메시지 배치(최대 10건). 존재하지 않는 case_id -> 워커가 무료 실패."""
    entries = []
    for i in range(n):
        body = {
            "type": "analyze_case",
            "case_id": f"loadtest-{uuid.uuid4()}",  # 존재하지 않는 사건 -> DB 조회 실패(비용 0)
            "lang": "ko",
        }
        entries.append({"Id": str(start_idx + i), "MessageBody": json.dumps(body)})
    return entries


def send_all(sqs, queue_url: str, count: int, workers: int) -> int:
    """count건을 10건 배치 send-message-batch로 병렬 투입. 보낸 건수 반환."""
    batches = []
    idx = 0
    remaining = count
    while remaining > 0:
        n = min(10, remaining)
        batches.append(make_entries(n, idx))
        idx += n
        remaining -= n

    sent = 0
    lock_sent = [0]

    def send_batch(entries):
        resp = sqs.send_message_batch(QueueUrl=queue_url, Entries=entries)
        return len(resp.get("Successful", [])), len(resp.get("Failed", []))

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(send_batch, b) for b in batches]
        for i, f in enumerate(concurrent.futures.as_completed(futures)):
            ok, failed = f.result()
            sent += ok
            if (i + 1) % 50 == 0:
                print(f"  ... {sent}건 전송")
    return sent


def queue_depth(sqs, queue_url: str) -> tuple[int, int, int]:
    """(visible, in-flight, oldest_message_age_seconds).

    참고: ApproximateAgeOfOldestMessage는 GetQueueAttributes의 유효 속성이 아니라
    CloudWatch(AWS/SQS) 지표다. 큐 속성으로 요청하면 InvalidAttributeName 에러가 나므로
    여기서는 visible/in-flight만 큐 속성으로 조회하고, oldest-age는 CloudWatch/Grafana에서 본다.
    """
    attrs = sqs.get_queue_attributes(
        QueueUrl=queue_url,
        AttributeNames=[
            "ApproximateNumberOfMessages",
            "ApproximateNumberOfMessagesNotVisible",
        ],
    )["Attributes"]
    return (
        int(attrs["ApproximateNumberOfMessages"]),
        int(attrs["ApproximateNumberOfMessagesNotVisible"]),
        0,
    )


def watch_drain(sqs, queue_url: str, interval: int, timeout: int) -> None:
    """큐가 빌 때까지 depth와 oldest-message age를 주기적으로 출력(드레인 곡선 캡처용).

    컬럼: elapsed_s,visible,in_flight,oldest_age_s
    스케일아웃 효과 = oldest_age가 치솟았다가 Worker 증설 후 꺾여 내려오고 visible이 0으로 소진되는 곡선.
    CloudWatch/Grafana의 ApproximateAgeOfOldestMessage + Worker RunningTaskCount 그래프와 대조한다.
    """
    print("\n=== 드레인 관측 시작 (Ctrl+C 중단) ===")
    print("elapsed_s,visible,in_flight,oldest_age_s")
    t0 = time.time()
    peak_visible = 0
    peak_age = 0
    drained_at = None
    try:
        while True:
            elapsed = time.time() - t0
            visible, inflight, age = queue_depth(sqs, queue_url)
            peak_visible = max(peak_visible, visible)
            peak_age = max(peak_age, age)
            print(f"{elapsed:7.0f},{visible},{inflight},{age}")
            if visible == 0 and inflight == 0 and elapsed > interval:
                drained_at = elapsed
                break
            if elapsed >= timeout:
                print(f"# timeout {timeout}s 도달 — 관측 종료 (잔여 visible={visible})")
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        print("# 사용자 중단")
    print("=== 드레인 관측 종료 ===")
    print(f"peak: visible~{peak_visible}, oldest_age~{peak_age}s")
    if drained_at is not None:
        print(f"드레인 완료 소요: ~{drained_at:.0f}s (peak visible {peak_visible} -> 0)")


def main():
    ap = argparse.ArgumentParser(description="BADA Worker 스케일 유발용 SQS 적체 생성기")
    ap.add_argument("--count", type=int, default=6000, help="투입할 메시지 수 (기본 6000)")
    ap.add_argument("--queue", default=DEFAULT_QUEUE, help="큐 이름 또는 URL")
    ap.add_argument("--region", default=DEFAULT_REGION)
    ap.add_argument("--profile", default=None, help="AWS 프로파일 (미지정 시 기본 체인/AWS_PROFILE)")
    ap.add_argument("--workers", type=int, default=20, help="병렬 전송 스레드 수")
    ap.add_argument("--purge", action="store_true", help="큐를 비우고 종료(테스트 정리용)")
    ap.add_argument("--watch", action="store_true", help="전송 후 큐가 빌 때까지 depth/oldest-age 주기 출력(드레인 곡선). --count 0과 함께 쓰면 관측만.")
    ap.add_argument("--watch-interval", type=int, default=15, help="--watch 폴링 간격(초, 기본 15)")
    ap.add_argument("--watch-timeout", type=int, default=1800, help="--watch 최대 관측 시간(초, 기본 1800)")
    args = ap.parse_args()

    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    sqs = session.client("sqs")
    queue_url = resolve_queue_url(sqs, args.queue)
    print(f"queue: {queue_url}")

    if args.purge:
        visible, inflight, age = queue_depth(sqs, queue_url)
        print(f"purge 전 depth: visible={visible}, in-flight={inflight}, oldest_age={age}s")
        sqs.purge_queue(QueueUrl=queue_url)
        print("purge 요청 완료 (최대 60초 내 반영). 실제 트래픽 없는 창에서만 사용하세요.")
        return

    visible0, inflight0, age0 = queue_depth(sqs, queue_url)
    print(f"시작 depth: visible={visible0}, in-flight={inflight0}, oldest_age={age0}s")

    if args.count > 0:
        print(f"{args.count}건 투입 시작...")
        t0 = time.time()
        sent = send_all(sqs, queue_url, args.count, args.workers)
        dt = time.time() - t0
        print(f"완료: {sent}건 전송 ({dt:.1f}s, {sent / dt:.0f} msg/s)")
        visible1, inflight1, age1 = queue_depth(sqs, queue_url)
        print(f"투입 후 depth: visible={visible1}, in-flight={inflight1}, oldest_age={age1}s")
    else:
        print("--count 0 → 전송 생략 (관측만).")

    print("\n이제 Worker가 backlog를 소비하며 scale-out(1->2->3) 해야 합니다.")
    print("확인: aws application-autoscaling describe-scaling-activities --service-namespace ecs \\")
    print(f"  --region {args.region} --profile {args.profile or 'bada-team'} \\")
    print("  --resource-id service/bada-dev-cluster/bada-dev-worker --output table")

    if args.watch:
        watch_drain(sqs, queue_url, args.watch_interval, args.watch_timeout)
    else:
        print("드레인 곡선 캡처: --watch (elapsed/visible/in-flight/oldest_age 주기 출력)")
    print("정리: python load-test/sqs/fill_backlog.py --purge")


if __name__ == "__main__":
    main()

"""BADA 인프라 — AWS 관리형 단일 노선(tech.md). K8s/Kafka 금지.

W1 bolt에서 각 리소스를 채운다. 아래는 구조 골격 + TODO.
필요 리소스: VPC, RDS(PostgreSQL+PostGIS), S3+KMS, SQS, Cognito, ECS Fargate(API+Worker), API GW.
"""
from aws_cdk import Stack
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_sqs as sqs
from aws_cdk import aws_kms as kms
from constructs import Construct


class BadaStack(Stack):
    def __init__(self, scope: Construct, cid: str, **kwargs) -> None:
        super().__init__(scope, cid, **kwargs)

        # KMS 키 (S3 암호화 — security.md)
        key = kms.Key(self, "EvidenceKey", enable_key_rotation=True)

        # S3 — 원본 증거 + 생성 PDF (KMS 암호화, 퍼블릭 차단)
        s3.Bucket(
            self, "EvidenceBucket",
            encryption=s3.BucketEncryption.KMS,
            encryption_key=key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
        )

        # SQS — 분석 작업 큐
        sqs.Queue(self, "AnalysisQueue")

        # TODO(W1):
        #  - VPC + RDS PostgreSQL (PostGIS 확장은 부팅 후 CREATE EXTENSION postgis)
        #  - Cognito User Pool + Client
        #  - ECS Fargate: backend 서비스 + worker 서비스, API Gateway 연결
        #  - CloudWatch 알람(비용/에러), Bedrock 모델 액세스는 콘솔에서 활성화

# 유닛 1: 인프라 및 보안 — 인프라 설계

## Terraform 변경 사항

### 1. ACM 인증서
```hcl
resource "aws_acm_certificate" "main" {
  domain_name               = "badasoft.com"
  subject_alternative_names = ["*.badasoft.com"]
  validation_method         = "DNS"
}

resource "aws_route53_record" "cert_validation" {
  for_each = { for dvo in aws_acm_certificate.main.domain_validation_options : dvo.domain_name => dvo }

  zone_id = data.aws_route53_zone.main.zone_id
  name    = each.value.resource_record_name
  type    = each.value.resource_record_type
  records = [each.value.resource_record_value]
  ttl     = 60
}

data "aws_route53_zone" "main" {
  name = "badasoft.com"
}
```
- Route 53에서 구매했으므로 호스팅 영역이 이미 존재
- Terraform이 DNS 검증 레코드를 자동 생성 → 인증서 즉시 발급

### 2. ALB HTTPS Listener
```hcl
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate.main.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }
}
```

### 3. HTTP → HTTPS 리다이렉트
```hcl
resource "aws_lb_listener" "http_redirect" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}
```

### 4. 호스트 기반 라우팅 + Route 53 DNS
```hcl
resource "aws_lb_listener_rule" "frontend" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 10

  condition {
    host_header { values = ["badasoft.com", "www.badasoft.com"] }
  }
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}

resource "aws_lb_listener_rule" "api" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 20

  condition {
    host_header { values = ["api.badasoft.com"] }
  }
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }
}

# Route 53 A 레코드 (ALB Alias)
resource "aws_route53_record" "frontend" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = "badasoft.com"
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "api" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = "api.badasoft.com"
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}
```

### 5. ALB Access Logging
```hcl
resource "aws_lb" "main" {
  # 기존 설정 + access_logs 추가
  access_logs {
    bucket  = aws_s3_bucket.alb_logs.id
    prefix  = "alb"
    enabled = true
  }
}

resource "aws_s3_bucket" "alb_logs" {
  bucket = "${local.name_prefix}-alb-logs"
}
```

### 6. Frontend ECS 기반 (유닛 5에서 태스크 정의, 여기서는 ECR + Target Group만)
```hcl
resource "aws_ecr_repository" "frontend" {
  name = "${local.name_prefix}-frontend"
}

resource "aws_lb_target_group" "frontend" {
  name        = "${local.name_prefix}-fe"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    path = "/"
    port = "3000"
  }
}
```

### 7. Worker desired_count 전환
```hcl
resource "aws_ecs_service" "worker" {
  # 기존 설정에서 desired_count만 변경
  desired_count = 1  # 0 → 1
}
```

### 8. Security Group 검토
- ALB SG: 인바운드 80, 443 from `0.0.0.0/0` (공개) ✅
- Backend SG: 인바운드 8000 from ALB SG only ✅
- Worker SG: 인바운드 없음, 아웃바운드 전체 ✅
- RDS SG: 인바운드 5432 from Backend SG + Worker SG only ✅

---

## Backend 코드 변경

### 보안 미들웨어 (`backend/app/middleware/security.py` 신규)
- `SecurityHeadersMiddleware`: 모든 응답에 보안 헤더 추가
- `RateLimitMiddleware`: IP 기반 60req/min, 인메모리 딕셔너리

### main.py 변경
- CORS: `allow_origins=["*"]` → 실제 도메인 목록
- 미들웨어 등록: `SecurityHeadersMiddleware`, `RateLimitMiddleware`

---

## 배포 순서

1. Terraform apply (ACM, HTTPS listener, ALB logs, Frontend ECR/TG, Worker desired=1)
2. Backend 코드 배포 (보안 미들웨어 추가)
3. 검증: HTTPS 동작, 보안 헤더, CORS 차단, Rate limit, Worker 실행 상태

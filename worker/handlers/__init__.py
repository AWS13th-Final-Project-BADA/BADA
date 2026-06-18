"""SQS 메시지 작업별 handler 패키지.

각 handler는 동일한 인터페이스를 따른다:

    def handle(message: dict) -> None

consumer.py 는 메시지 종류를 보고 알맞은 handler.handle() 을 호출만 하며,
내부 구현(백엔드 호출/직접 DB 등)은 알지 못한다. → handler 교체 시 consumer 불변.
"""

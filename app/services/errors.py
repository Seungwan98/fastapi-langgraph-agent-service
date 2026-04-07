from __future__ import annotations
class ModelProviderError(Exception):
    def __init__(self, message: str, *, thread_id: str | None = None, model: str | None = None):
        """프로바이더 실패 문맥을 오류 메시지와 함께 보관한다."""
        super().__init__(message)
        self.thread_id = thread_id
        self.model = model

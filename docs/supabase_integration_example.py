"""LangGraph 체크포인팅용 Supabase 연동 예시"""

# 방법 1: PostgresCheckpoint 사용(가장 단순함)
# 필요 패키지: langgraph-checkpoint-postgres psycopg2-binary

from langgraph.checkpoint.postgres import PostgresCheckpoint


def build_supabase_checkpointer(connection_url: str):
    """Supabase PostgreSQL 기반 체크포인터를 만든다."""
    # Supabase 연결 URL 형식:
    # postgresql://postgres:[PASSWORD]@db.[PROJECT_ID].supabase.co:5432/postgres
    return PostgresCheckpoint(connection_url)


# 방법 2: 커스텀 Supabase 세이버(제어 범위가 더 넓음)
# 필요 패키지: supabase

from typing import Any
from supabase import create_client


class SupabaseCheckpoint:
    """Supabase를 사용하는 커스텀 체크포인트 저장기다."""
    
    def __init__(self, url: str, key: str):
        """체크포인트 저장용 Supabase 클라이언트를 만든다."""
        self.client = create_client(url, key)
    
    def get(self, thread_id: str) -> dict[str, Any] | None:
        """Supabase에서 체크포인트를 조회한다."""
        result = self.client.table("checkpoints").select("*").eq("thread_id", thread_id).execute()
        if result.data:
            return result.data[0]["state"]
        return None
    
    def put(self, thread_id: str, state: dict[str, Any]) -> None:
        """체크포인트를 Supabase에 저장한다."""
        self.client.table("checkpoints").upsert({
            "thread_id": thread_id,
            "state": state,
        }).execute()


# 방법 3: 비동기 지원(프로덕션용)
# 필요 패키지: asyncpg

from langgraph.checkpoint.postgres.aio import AsyncPostgresCheckpoint


def build_async_supabase_checkpointer(connection_url: str):
    """더 나은 성능을 위해 비동기 체크포인터를 만든다."""
    return AsyncPostgresCheckpoint(connection_url)

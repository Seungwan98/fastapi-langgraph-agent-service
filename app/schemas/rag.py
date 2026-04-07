from pydantic import BaseModel


class RAGRebuildResponse(BaseModel):
    status: str
    document_count: int
    chunk_count: int
    output_path: str
    embedding_model: str
    chunk_size: int
    chunk_overlap: int

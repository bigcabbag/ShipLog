from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="用户问题")
    system_prompt: str | None = Field(
        default=None,
        description="可选系统提示词，用来设定 AI 角色",
    )
    use_rag: bool = Field(
        default=True,
        description="是否基于已上传文档回答（M2.3 RAG）",
    )
    top_k: int = Field(
        default=3,
        ge=1,
        le=10,
        description="检索返回的文档块数量",
    )


class SourceChunk(BaseModel):
    source: str
    page: int | str
    content: str


class ChatResponse(BaseModel):
    reply: str
    model: str
    sources: list[SourceChunk] | None = None
    trace_id: str | None = Field(
        default=None,
        description="RAG 请求 trace_id，可用于 GET /traces/{trace_id} 回放检索过程",
    )


class ChunkPreview(BaseModel):
    index: int
    content: str
    metadata: dict


class UploadResponse(BaseModel):
    filename: str
    chunk_count: int
    chunk_size: int
    chunk_overlap: int
    indexed_chunks: int
    vector_count: int
    embedding_model: str
    previews: list[ChunkPreview]


class IndexStatsResponse(BaseModel):
    collection: str
    vector_count: int
    embedding_model: str

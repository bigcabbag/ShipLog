from pydantic import BaseModel, Field, model_validator


class ChatRequest(BaseModel):
    message: str = Field(default="", description="用户问题（可空，若附带截图）")
    image_base64: str | None = Field(
        default=None,
        description="可选告警截图 base64（不含 data: 前缀）",
    )
    image_media_type: str = Field(
        default="image/png",
        description="截图 MIME，如 image/png、image/jpeg",
    )
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
    thread_id: str | None = Field(
        default=None,
        description="M6.2：On-call 会话 thread_id，多轮对话共用",
    )

    @model_validator(mode="after")
    def message_or_image(self) -> "ChatRequest":
        if not self.message.strip() and not self.image_base64:
            raise ValueError("message 与 image_base64 至少提供一个")
        if self.image_base64 and not self.use_rag:
            raise ValueError("截图提问需开启 use_rag")
        return self


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
    extracted_query: str | None = Field(
        default=None,
        description="M5.3：从截图提取的检索 query（无图时为 null）",
    )
    thread_id: str | None = Field(
        default=None,
        description="M6.2：会话 thread_id",
    )
    plan_steps: list[str] | None = Field(
        default=None,
        description="M6.2：排查计划步骤",
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

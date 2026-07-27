import { useCallback, useEffect, useRef, useState } from "react";
import {
  fetchDocumentStats,
  uploadDocument,
  type IndexStats,
  type UploadResult,
} from "../api/documents";
import "./UploadPanel.css";

type UploadPanelProps = {
  disabled?: boolean;
};

function UploadPanel({ disabled = false }: UploadPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [stats, setStats] = useState<IndexStats | null>(null);
  const [statsError, setStatsError] = useState<string | null>(null);
  const [loadingStats, setLoadingStats] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [lastUpload, setLastUpload] = useState<UploadResult | null>(null);

  const refreshStats = useCallback(async () => {
    if (disabled) return;
    setLoadingStats(true);
    setStatsError(null);
    try {
      const data = await fetchDocumentStats();
      setStats(data);
    } catch (err: unknown) {
      setStatsError(err instanceof Error ? err.message : "加载统计失败");
    } finally {
      setLoadingStats(false);
    }
  }, [disabled]);

  useEffect(() => {
    void refreshStats();
  }, [refreshStats]);

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || uploading || disabled) return;

    const lower = file.name.toLowerCase();
    if (!lower.endsWith(".pdf") && !lower.endsWith(".md")) {
      setUploadError("目前只支持 PDF 或 Markdown（.pdf / .md）");
      return;
    }

    setUploading(true);
    setUploadError(null);
    setLastUpload(null);

    try {
      const result = await uploadDocument(file);
      setLastUpload(result);
      setStats({
        collection: stats?.collection ?? "rag_documents",
        vector_count: result.vector_count,
        embedding_model: result.embedding_model,
      });
      await refreshStats();
    } catch (err: unknown) {
      setUploadError(err instanceof Error ? err.message : "上传失败");
    } finally {
      setUploading(false);
    }
  }

  return (
    <section className="upload-panel card">
      <h2>知识库</h2>
      <p className="upload-panel__hint">上传 PDF / Markdown → 切块 → 写入向量库</p>

      <div className="upload-panel__stats">
        <div className="upload-panel__stat-row">
          <span className="upload-panel__stat-label">向量总数</span>
          <strong className="upload-panel__stat-value">
            {loadingStats ? "…" : (stats?.vector_count ?? "—")}
          </strong>
        </div>
        <div className="upload-panel__stat-row">
          <span className="upload-panel__stat-label">Embedding</span>
          <code className="upload-panel__stat-code">
            {stats?.embedding_model ?? "—"}
          </code>
        </div>
        {statsError && <p className="upload-panel__error">{statsError}</p>}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.md,application/pdf,text/markdown"
        className="upload-panel__file-input"
        disabled={disabled || uploading}
        onChange={(e) => void handleFileChange(e)}
      />
      <button
        type="button"
        className="upload-panel__upload-btn"
        disabled={disabled || uploading}
        onClick={() => inputRef.current?.click()}
      >
        {uploading ? "上传并索引中…" : "选择 PDF / Markdown 上传"}
      </button>

      {uploadError && <p className="upload-panel__error">{uploadError}</p>}

      {lastUpload && (
        <div className="upload-panel__result">
          <p className="upload-panel__result-title">✅ {lastUpload.filename}</p>
          <ul>
            <li>切块：{lastUpload.chunk_count}（size {lastUpload.chunk_size}，overlap {lastUpload.chunk_overlap}）</li>
            <li>本次写入向量：{lastUpload.indexed_chunks}</li>
            <li>库内向量总数：{lastUpload.vector_count}</li>
          </ul>
          {lastUpload.previews.length > 0 && (
            <details>
              <summary>预览前 {lastUpload.previews.length} 块</summary>
              {lastUpload.previews.map((p) => (
                <pre key={p.index} className="upload-panel__preview">
                  [{p.index}] {p.content}
                </pre>
              ))}
            </details>
          )}
        </div>
      )}

      <button
        type="button"
        className="upload-panel__refresh"
        disabled={disabled || loadingStats}
        onClick={() => void refreshStats()}
      >
        刷新统计
      </button>
    </section>
  );
}

export default UploadPanel;

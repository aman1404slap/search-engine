import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";

const POLL_MS = 2000;

const STATUS_LABELS = {
  parsing: "Parsing…",
  processing_media: "Generating thumbnails & embeddings…",
  completed: "Completed",
  completed_with_errors: "Completed with errors",
  failed: "Failed",
};

function pipelinePct(upload) {
  if (upload.pipeline_status === "parsing") {
    return upload.total_records
      ? Math.round(((upload.processed_records + upload.failed_records) / upload.total_records) * 100)
      : 0;
  }
  if (upload.pipeline_status === "processing_media") {
    return upload.total_records
      ? Math.round(((upload.videos_ready + upload.videos_failed_media) / upload.total_records) * 100)
      : 0;
  }
  return 100;
}

export default function UploadsScreen({ onIngested }) {
  const [uploads, setUploads] = useState([]);
  const [loaded, setLoaded] = useState(false);
  const [file, setFile] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const pollRef = useRef(null);
  const fileInputRef = useRef(null);
  const wasActiveRef = useRef(false);

  async function refresh() {
    try {
      const res = await api.getUploads();
      const list = res.results ?? res;
      setUploads(list);
      setLoaded(true);

      const stillActive = list.some((u) => u.is_active);
      if (wasActiveRef.current && !stillActive) onIngested?.();
      wasActiveRef.current = stillActive;
    } catch (err) {
      setError(err);
    }
  }

  useEffect(() => {
    refresh();
    pollRef.current = setInterval(refresh, POLL_MS);
    return () => clearInterval(pollRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const latest = uploads[0];
  const blocked = !!latest?.is_active;

  async function submit(e) {
    e.preventDefault();
    if (!file || blocked) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.uploadJsonl(file);
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      await refresh();
    } catch (err) {
      setError(err);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="uploads-screen">
      <div className="uploads-screen__header">
        <h1>Uploads</h1>
        <p className="modal__hint">
          Upload a JSONL file (one video record per line) matching the ego-assist schema. Each
          upload is parsed, then every video's thumbnail and search embeddings are generated in
          the background. Only one upload can be in flight at a time.
        </p>
      </div>

      <form onSubmit={submit} className="upload-form uploads-screen__form">
        <input
          ref={fileInputRef}
          type="file"
          accept=".jsonl,.json,application/json"
          onChange={(e) => setFile(e.target.files[0])}
          disabled={submitting || blocked}
        />
        <button type="submit" disabled={!file || submitting || blocked}>
          {submitting ? "Uploading…" : "Upload"}
        </button>
      </form>

      {blocked && (
        <p className="uploads-screen__blocked">
          "{latest.file_name}" is still {(STATUS_LABELS[latest.pipeline_status] ?? "processing").toLowerCase()} — new
          uploads are disabled until it finishes.
        </p>
      )}
      {error && <p className="form-error">{error.message}</p>}

      <div className="uploads-screen__list">
        {!loaded && <p className="modal__hint">Loading…</p>}
        {loaded && uploads.length === 0 && <p className="modal__hint">No uploads yet.</p>}
        {uploads.map((u) => (
          <UploadRow key={u.id} upload={u} />
        ))}
      </div>
    </div>
  );
}

function UploadRow({ upload }) {
  const pct = pipelinePct(upload);

  return (
    <div className="uploads-row">
      <div className="uploads-row__main">
        <span className="uploads-row__name">{upload.file_name}</span>
        <span className={`uploads-row__status uploads-row__status--${upload.pipeline_status}`}>
          {upload.is_active && <span className="spinner spinner--small" />}
          {STATUS_LABELS[upload.pipeline_status] ?? upload.pipeline_status}
        </span>
      </div>

      <div className="upload-progress__bar">
        <div
          className={`upload-progress__fill upload-progress__fill--${upload.pipeline_status}`}
          style={{ width: `${pct}%` }}
        />
      </div>

      <div className="uploads-row__meta">
        <span>{upload.processed_records} parsed</span>
        {upload.failed_records > 0 && (
          <span className="uploads-row__meta--danger">{upload.failed_records} parse errors</span>
        )}
        <span>{upload.videos_ready} ready</span>
        {upload.videos_processing > 0 && <span>{upload.videos_processing} processing</span>}
        {upload.videos_failed_media > 0 && (
          <span className="uploads-row__meta--danger">{upload.videos_failed_media} media errors</span>
        )}
        <span className="uploads-row__time">{new Date(upload.created_at).toLocaleString()}</span>
      </div>

      {upload.error_message && <p className="form-error">{upload.error_message}</p>}
    </div>
  );
}

import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import Modal from "./Modal";

const POLL_MS = 1500;

export default function UploadModal({ onClose, onIngested }) {
  const [file, setFile] = useState(null);
  const [upload, setUpload] = useState(null);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const pollRef = useRef(null);

  useEffect(() => () => clearInterval(pollRef.current), []);

  function poll(uploadId) {
    pollRef.current = setInterval(async () => {
      try {
        const res = await api.getUpload(uploadId);
        setUpload(res);
        if (res.status !== "processing") {
          clearInterval(pollRef.current);
          onIngested?.();
        }
      } catch (err) {
        clearInterval(pollRef.current);
        setError(err);
      }
    }, POLL_MS);
  }

  async function submit(e) {
    e.preventDefault();
    if (!file) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await api.uploadJsonl(file);
      setUpload({ ...res, processed_records: 0, failed_records: 0 });
      poll(res.upload_id);
    } catch (err) {
      setError(err);
    } finally {
      setSubmitting(false);
    }
  }

  const pct = upload?.total_records
    ? Math.round(((upload.processed_records + upload.failed_records) / upload.total_records) * 100)
    : 0;

  return (
    <Modal title="Upload video metadata (JSONL)" onClose={onClose}>
      <p className="modal__hint">
        Upload a JSONL file (one video record per line) matching the ego-assist schema. Videos are
        matched to S3 via their <code>provenance.source</code> path. Thumbnails, durations and
        search embeddings are generated automatically in the background.
      </p>
      <form onSubmit={submit} className="upload-form">
        <input
          type="file"
          accept=".jsonl,.json,application/json"
          onChange={(e) => setFile(e.target.files[0])}
          disabled={submitting || upload?.status === "processing"}
        />
        <button type="submit" disabled={!file || submitting || upload?.status === "processing"}>
          {submitting ? "Uploading…" : "Upload"}
        </button>
      </form>

      {error && <p className="form-error">{error.message}</p>}

      {upload && (
        <div className="upload-progress">
          <div className="upload-progress__bar">
            <div className="upload-progress__fill" style={{ width: `${pct}%` }} />
          </div>
          <p>
            {upload.status === "processing"
              ? `Processing… ${upload.processed_records + upload.failed_records}/${upload.total_records}`
              : `${upload.status.replace(/_/g, " ")} — ${upload.processed_records} ingested, ${
                  upload.failed_records
                } failed`}
          </p>
          {upload.status !== "processing" && (
            <p className="modal__hint">
              Thumbnails and embeddings continue processing in the background for a few more
              seconds per video — refresh the grid shortly if a thumbnail is still missing.
            </p>
          )}
        </div>
      )}
    </Modal>
  );
}

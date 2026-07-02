import { formatTime, humanize } from "../utils/format";

const SINGLE_FACETS = [
  "request",
  "interaction_pattern",
  "capture_medium",
  "capture_quality",
  "setting",
  "weather",
  "environment_domain",
  "outcome",
];

const MULTI_FACETS = ["secondary_requests", "reasoning_demands", "target_entity", "perceptual_properties"];

export default function MetadataPanel({ video }) {
  if (!video) return null;
  const taxonomy = video.taxonomy || {};

  return (
    <div className="metadata-panel">
      <section>
        <h3>Summary</h3>
        <p className="metadata-panel__lead">{video.assist_brief}</p>
        {video.assist_detailed && video.assist_detailed !== video.assist_brief && (
          <p className="metadata-panel__detail">{video.assist_detailed}</p>
        )}
      </section>

      <section>
        <h3>Request</h3>
        <p className="metadata-panel__lead">{video.request_brief}</p>
        {video.request_detailed && video.request_detailed !== video.request_brief && (
          <p className="metadata-panel__detail">{video.request_detailed}</p>
        )}
        {video.request_confidence && (
          <span className={`badge badge--${video.request_confidence}`}>
            {humanize(video.request_confidence)} confidence
          </span>
        )}
      </section>

      <section>
        <h3>Taxonomy</h3>
        <div className="tag-grid">
          {SINGLE_FACETS.filter((f) => taxonomy[f]).map((f) => (
            <div key={f} className="tag-grid__item">
              <span className="tag-grid__key">{humanize(f)}</span>
              <span className="chip">{humanize(taxonomy[f])}</span>
            </div>
          ))}
        </div>
        {MULTI_FACETS.map(
          (f) =>
            taxonomy[f]?.length > 0 && (
              <div key={f} className="tag-grid__item tag-grid__item--wide">
                <span className="tag-grid__key">{humanize(f)}</span>
                <div className="video-card__chips">
                  {taxonomy[f].map((v) => (
                    <span key={v} className="chip">
                      {humanize(v)}
                    </span>
                  ))}
                </div>
              </div>
            )
        )}
      </section>

      <section className="metadata-panel__meta-row">
        {video.duration_sec != null && <span>⏱ {formatTime(video.duration_sec)}</span>}
        {video.caller_state && (
          <span>
            📍 {video.caller_state}
            {video.caller_country ? `, ${video.caller_country}` : ""}
          </span>
        )}
        {video.detected_language && <span>🌐 {video.detected_language.toUpperCase()}</span>}
        {video.source_label && <span>🏷 {humanize(video.source_label)}</span>}
        <span>
          📼 {video.ingestion_status === "ready" ? "Ready" : humanize(video.ingestion_status)}
        </span>
      </section>

      {video.segments?.length > 0 && (
        <section>
          <h3>Events ({video.segments.length})</h3>
          <ol className="segment-list">
            {video.segments.map((seg) => (
              <li key={seg.segment_id}>
                <span className="segment-list__time">
                  {formatTime(seg.start_s)}–{formatTime(seg.end_s)}
                </span>
                <span>{seg.text}</span>
              </li>
            ))}
          </ol>
        </section>
      )}

      {video.transcript?.length > 0 && (
        <section>
          <h3>Transcript</h3>
          <ol className="transcript-list">
            {video.transcript.map((t, i) => (
              <li key={i}>
                <span className="transcript-list__time">{formatTime(t.start_s)}</span>
                <span className="transcript-list__speaker">{humanize(t.speaker_id)}:</span>
                <span>{t.text}</span>
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}

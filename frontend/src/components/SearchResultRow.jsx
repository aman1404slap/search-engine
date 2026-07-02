import { formatTime, humanize, confidenceLabel } from "../utils/format";

export default function SearchResultRow({ video, resultMeta, selected, onClick }) {
  const taxonomy = video.taxonomy || {};
  const chips = [
    ...new Set(
      [taxonomy.request, taxonomy.environment_domain, taxonomy.capture_medium].filter(Boolean)
    ),
  ];

  return (
    <button
      className={`search-result-row ${selected ? "search-result-row--selected" : ""}`}
      onClick={onClick}
      type="button"
    >
      <div className="search-result-row__thumb">
        {video.thumbnail_url ? (
          <img src={video.thumbnail_url} alt="" loading="lazy" />
        ) : (
          <div className="video-card__thumb-placeholder">
            {video.ingestion_status === "processing" || video.ingestion_status === "pending" ? (
              <span className="spinner" />
            ) : (
              <span>No preview</span>
            )}
          </div>
        )}
      </div>

      <div className="search-result-row__body">
        <p className="search-result-row__text">
          {resultMeta ? resultMeta.matched_text : video.assist_brief || video.request_brief}
        </p>
        <div className="search-result-row__chips">
          {chips.map((c) => (
            <span key={c} className="chip">
              {humanize(c)}
            </span>
          ))}
          {!resultMeta && video.ingestion_status && video.ingestion_status !== "ready" && (
            <span className="chip chip--status">{humanize(video.ingestion_status)}</span>
          )}
        </div>
      </div>

      <div className="search-result-row__meta">
        {resultMeta ? (
          <>
            <span
              className={`video-card__confidence video-card__confidence--${confidenceLabel(
                resultMeta.confidence
              )}`}
            >
              {Math.round(resultMeta.confidence * 100)}%
            </span>
            <span className="search-result-row__timespan">
              {formatTime(resultMeta.start_s)}&ndash;{formatTime(resultMeta.end_s)}
            </span>
          </>
        ) : (
          video.duration_sec != null && (
            <span className="search-result-row__timespan">{formatTime(video.duration_sec)}</span>
          )
        )}
      </div>
    </button>
  );
}

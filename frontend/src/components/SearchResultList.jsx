import SearchResultRow from "./SearchResultRow";

const LOW_CONFIDENCE_THRESHOLD = 0.6;

export default function SearchResultList({
  mode,
  items,
  loading,
  error,
  selectedKey,
  onSelect,
  page,
  pageCount,
  onPageChange,
}) {
  const isSearch = mode === "search";

  if (loading) {
    return (
      <div className="video-grid__status">
        <span className="spinner" /> {isSearch ? "Searching" : "Loading videos"}&hellip;
      </div>
    );
  }
  if (error) {
    return <div className="video-grid__status video-grid__status--error">{error.message}</div>;
  }
  if (!items.length) {
    return (
      <div className="video-grid__status">
        {isSearch ? "No matches. Try a different query or fewer filters." : "No videos match these filters."}
      </div>
    );
  }

  function rowKey(item) {
    return isSearch ? item.video_id : item.shot_id;
  }

  function renderRow(item) {
    const video = isSearch ? item.video : item;
    const resultMeta = isSearch ? item : null;
    const key = rowKey(item);
    return (
      <SearchResultRow
        key={key}
        video={video}
        resultMeta={resultMeta}
        selected={key === selectedKey}
        onClick={() => onSelect(video.shot_id)}
      />
    );
  }

  if (!isSearch) {
    return (
      <div className="video-grid-wrap">
        <div className="search-result-list">{items.map(renderRow)}</div>
        {pageCount > 1 && (
          <div className="pagination">
            <button disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
              ← Prev
            </button>
            <span>
              Page {page} of {pageCount}
            </span>
            <button disabled={page >= pageCount} onClick={() => onPageChange(page + 1)}>
              Next →
            </button>
          </div>
        )}
      </div>
    );
  }

  const sorted = [...items].sort((a, b) => b.confidence - a.confidence);
  const high = sorted.filter((r) => r.confidence >= LOW_CONFIDENCE_THRESHOLD);
  const low = sorted.filter((r) => r.confidence < LOW_CONFIDENCE_THRESHOLD);

  return (
    <div className="search-result-list">
      {high.map(renderRow)}

      {high.length === 0 && (
        <div className="search-result-notice">No high confidence matches.</div>
      )}

      {low.length > 0 && (
        <>
          <div className="search-result-divider">Low score match</div>
          {low.map(renderRow)}
        </>
      )}
    </div>
  );
}

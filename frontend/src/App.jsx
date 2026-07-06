import { useEffect, useMemo, useState } from "react";
import { api } from "./api/client";
import { useAuth } from "./context/AuthContext";
import { useTaxonomy } from "./hooks/useTaxonomy";
import { useVideos } from "./hooks/useVideos";
import FilterSidebar from "./components/FilterSidebar";
import LoginForm from "./components/LoginForm";
import SearchBar from "./components/SearchBar";
import SearchResultList from "./components/SearchResultList";
import VideoPlayerPane from "./components/VideoPlayerPane";
import UploadModal from "./components/UploadModal";
import TaxonomyAdminModal from "./components/TaxonomyAdminModal";
import "./styles/app.css";

export default function App() {
  const { user, checking } = useAuth();

  if (checking) return null;
  if (!user) return <LoginForm />;
  return <VideoSearchApp />;
}

function VideoSearchApp() {
  const { user, logout } = useAuth();
  const { facets, reload: reloadTaxonomy } = useTaxonomy();

  const [filters, setFilters] = useState({});
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");

  const [searchResults, setSearchResults] = useState(null);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState(null);

  const [selectedVideoId, setSelectedVideoId] = useState(null);
  const [selectedSpan, setSelectedSpan] = useState(null);
  const [seekToken, setSeekToken] = useState(0);

  const [showUpload, setShowUpload] = useState(false);
  const [showTaxonomy, setShowTaxonomy] = useState(false);
  const [gridRefreshKey, setGridRefreshKey] = useState(0);

  const isSearchMode = query.length > 0;
  const browseParams = useMemo(
    () => ({ ...filters, _refresh: gridRefreshKey }),
    [filters, gridRefreshKey]
  );
  const browse = useVideos(browseParams, page, !isSearchMode);

  useEffect(() => {
    setPage(1);
  }, [filters, query]);

  useEffect(() => {
    if (!isSearchMode) {
      setSearchResults(null);
      return;
    }
    setSearching(true);
    setSearchError(null);
    api
      .search({ query, filters, top_k: 30, min_confidence: 0.3 })
      .then((res) => {
        setSearchResults(res.results);
        if (res.results.length) {
          const top = [...res.results].sort((a, b) => b.confidence - a.confidence)[0];
          setSelectedVideoId(top.video_id);
          setSelectedSpan(top);
          setSeekToken((t) => t + 1);
        }
      })
      .catch(setSearchError)
      .finally(() => setSearching(false));
  }, [query, filters, isSearchMode]);

  const spansForSelected = useMemo(() => {
    if (!isSearchMode || !searchResults || !selectedVideoId) return null;
    return searchResults
      .filter((r) => r.video_id === selectedVideoId)
      .sort((a, b) => a.start_s - b.start_s);
  }, [isSearchMode, searchResults, selectedVideoId]);

  function handleSelect(shotId, resultItem) {
    setSelectedVideoId(shotId);
    setSelectedSpan(resultItem || null);
    setSeekToken((t) => t + 1);
  }

  const pageCount = Math.max(1, Math.ceil((browse.data.count || 0) / 24));
  const selectedKey = isSearchMode
    ? selectedSpan
      ? `${selectedSpan.video_id}-${selectedSpan.start_s}`
      : null
    : selectedVideoId;

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar__brand">
          <span className="topbar__logo">▶</span>
          <span>Video Search</span>
        </div>
        <SearchBar onSearch={setQuery} searching={searching} initialValue={query} />
        <div className="topbar__actions">
          <button className="ghost-button" onClick={() => setShowTaxonomy(true)}>
            ⚙ Taxonomy
          </button>
          <button className="primary-button" onClick={() => setShowUpload(true)}>
            ⬆ Upload JSONL
          </button>
          <span className="topbar__user">{user}</span>
          <button className="ghost-button" onClick={logout}>
            Log out
          </button>
        </div>
      </header>

      <div className="app-body">
        {facets.length > 0 && <FilterSidebar facets={facets} filters={filters} onChange={setFilters} />}

        <main className="content">
          <SearchResultList
            mode={isSearchMode ? "search" : "browse"}
            items={isSearchMode ? searchResults || [] : browse.data.results}
            loading={isSearchMode ? searching : browse.loading}
            error={isSearchMode ? searchError : browse.error}
            selectedKey={selectedKey}
            onSelect={handleSelect}
            page={page}
            pageCount={pageCount}
            onPageChange={setPage}
          />
        </main>

        <VideoPlayerPane shotId={selectedVideoId} spans={spansForSelected} seekToken={seekToken} />
      </div>

      {showUpload && (
        <UploadModal
          onClose={() => setShowUpload(false)}
          onIngested={() => setGridRefreshKey((k) => k + 1)}
        />
      )}
      {showTaxonomy && (
        <TaxonomyAdminModal
          facets={facets}
          onClose={() => setShowTaxonomy(false)}
          onChanged={reloadTaxonomy}
        />
      )}
    </div>
  );
}

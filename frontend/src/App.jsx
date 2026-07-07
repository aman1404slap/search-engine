import { useEffect, useMemo, useState } from "react";
import { api } from "./api/client";
import { useAuth } from "./context/AuthContext";
import { useTaxonomy } from "./hooks/useTaxonomy";
import { useTheme } from "./hooks/useTheme";
import { useVideos } from "./hooks/useVideos";
import FilterSidebar from "./components/FilterSidebar";
import LoginForm from "./components/LoginForm";
import SearchBar from "./components/SearchBar";
import SearchResultList from "./components/SearchResultList";
import VideoPlayerPane from "./components/VideoPlayerPane";
import UploadsScreen from "./components/UploadsScreen";
import TaxonomyAdminModal from "./components/TaxonomyAdminModal";
import "./styles/app.css";

export default function App() {
  const { user, checking } = useAuth();
  const [theme, setTheme] = useTheme();

  if (checking) return null;
  if (!user) return <LoginForm />;
  return <VideoSearchApp theme={theme} onToggleTheme={() => setTheme(theme === "dark" ? "light" : "dark")} />;
}

function VideoSearchApp({ theme, onToggleTheme }) {
  const { user, logout } = useAuth();
  const { facets, reload: reloadTaxonomy } = useTaxonomy();

  const [filters, setFilters] = useState({});
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");

  const [searchResults, setSearchResults] = useState(null);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState(null);

  const [selectedVideoId, setSelectedVideoId] = useState(null);
  const [seekToken, setSeekToken] = useState(0);

  const [view, setView] = useState("browse"); // "browse" | "uploads"
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
        // One result per video already (the API groups multi-timeframe matches),
        // ranked by that video's best-matching moment.
        setSearchResults(res.results);
        if (res.results.length) {
          const top = [...res.results].sort((a, b) => b.confidence - a.confidence)[0];
          setSelectedVideoId(top.video_id);
          setSeekToken((t) => t + 1);
        }
      })
      .catch(setSearchError)
      .finally(() => setSearching(false));
  }, [query, filters, isSearchMode]);

  const spansForSelected = useMemo(() => {
    if (!isSearchMode || !searchResults || !selectedVideoId) return null;
    const match = searchResults.find((r) => r.video_id === selectedVideoId);
    return match ? [...match.spans].sort((a, b) => a.start_s - b.start_s) : null;
  }, [isSearchMode, searchResults, selectedVideoId]);

  function handleSelect(shotId) {
    setSelectedVideoId(shotId);
    setSeekToken((t) => t + 1);
  }

  const pageCount = Math.max(1, Math.ceil((browse.data.count || 0) / 24));
  const selectedKey = selectedVideoId;

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar__brand">
          <span className="topbar__logo">▶</span>
          <span>Video Search</span>
        </div>
        {view === "browse" && <SearchBar onSearch={setQuery} searching={searching} initialValue={query} />}
        <div className="topbar__actions">
          {view === "browse" ? (
            <>
              <button className="ghost-button" onClick={() => setShowTaxonomy(true)}>
                ⚙ Taxonomy
              </button>
              <button className="primary-button" onClick={() => setView("uploads")}>
                ⬆ Uploads
              </button>
            </>
          ) : (
            <button className="ghost-button" onClick={() => setView("browse")}>
              ← Back to search
            </button>
          )}
          <button
            className="ghost-button"
            onClick={onToggleTheme}
            title={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
          >
            {theme === "dark" ? "☀" : "🌙"}
          </button>
          <span className="topbar__user">{user}</span>
          <button className="ghost-button" onClick={logout}>
            Log out
          </button>
        </div>
      </header>

      {view === "uploads" ? (
        <UploadsScreen onIngested={() => setGridRefreshKey((k) => k + 1)} />
      ) : (
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

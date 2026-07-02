import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";

export function useVideos(filters, page, enabled = true) {
  const [data, setData] = useState({ count: 0, results: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const requestId = useRef(0);

  useEffect(() => {
    if (!enabled) return;
    const id = ++requestId.current;
    setLoading(true);
    api
      .getVideos({ ...filters, page, page_size: 24 })
      .then((res) => {
        if (id === requestId.current) setData(res);
      })
      .catch((err) => {
        if (id === requestId.current) setError(err);
      })
      .finally(() => {
        if (id === requestId.current) setLoading(false);
      });
  }, [filters, page, enabled]);

  return { data, loading, error };
}

export function useVideoFacetCounts(filters) {
  const [counts, setCounts] = useState({});
  const requestId = useRef(0);

  useEffect(() => {
    const id = ++requestId.current;
    api
      .getVideoFacetCounts(filters)
      .then((res) => {
        if (id === requestId.current) setCounts(res);
      })
      .catch(() => {});
  }, [filters]);

  return counts;
}

export function useVideoDetail(shotId) {
  const [video, setVideo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!shotId) {
      setVideo(null);
      return;
    }
    setLoading(true);
    setError(null);
    api
      .getVideo(shotId)
      .then(setVideo)
      .catch(setError)
      .finally(() => setLoading(false));
  }, [shotId]);

  return { video, loading, error };
}

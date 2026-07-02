import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";

export function useTaxonomy() {
  const [facets, setFacets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const reload = useCallback(() => {
    setLoading(true);
    api
      .getTaxonomy()
      .then((data) => setFacets(data))
      .catch((err) => setError(err))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  return { facets, loading, error, reload };
}

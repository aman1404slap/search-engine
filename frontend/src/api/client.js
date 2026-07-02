const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: options.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail;
    try {
      detail = await res.json();
    } catch {
      detail = { error: res.statusText };
    }
    const err = new Error(detail.error || detail.detail || `Request failed: ${res.status}`);
    err.status = res.status;
    err.detail = detail;
    throw err;
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  getTaxonomy: () => request("/api/taxonomy/"),
  addTaxonomyValue: (facetKey, body) =>
    request(`/api/taxonomy/${facetKey}/values/`, { method: "POST", body: JSON.stringify(body) }),
  updateTaxonomyValue: (facetKey, value, body) =>
    request(`/api/taxonomy/${facetKey}/values/${value}/`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  deleteTaxonomyValue: (facetKey, value) =>
    request(`/api/taxonomy/${facetKey}/values/${value}/`, { method: "DELETE" }),

  getVideos: (params) => request(`/api/videos/?${buildQuery(params)}`),
  getVideoFacetCounts: (params) => request(`/api/videos/facets/?${buildQuery(params)}`),
  getVideo: (shotId) => request(`/api/videos/${encodeURIComponent(shotId)}/`),
  getPlayUrl: (shotId) => request(`/api/videos/${encodeURIComponent(shotId)}/play-url/`),

  search: (body) => request("/api/search/", { method: "POST", body: JSON.stringify(body) }),

  uploadJsonl: (file) => {
    const form = new FormData();
    form.append("file", file);
    return request("/api/ingestion/upload/", { method: "POST", body: form });
  },
  getUploads: () => request("/api/ingestion/uploads/"),
  getUpload: (id) => request(`/api/ingestion/uploads/${id}/`),
};

function buildQuery(params = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    if (Array.isArray(value)) {
      value.forEach((v) => v !== "" && search.append(key, v));
    } else {
      search.append(key, value);
    }
  });
  return search.toString();
}

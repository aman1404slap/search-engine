import { useVideoFacetCounts } from "../hooks/useVideos";

function toggleMultiValue(values, value) {
  return values.includes(value) ? values.filter((v) => v !== value) : [...values, value];
}

export default function FilterSidebar({ facets, filters, onChange }) {
  const counts = useVideoFacetCounts(filters);
  const activeCount = Object.values(filters).reduce(
    (sum, v) => sum + (Array.isArray(v) ? v.length : v ? 1 : 0),
    0
  );

  function setSingle(facetKey, value) {
    const next = { ...filters };
    if (next[facetKey] === value) {
      delete next[facetKey];
    } else {
      next[facetKey] = value;
    }
    onChange(next);
  }

  function setMulti(facetKey, value) {
    const next = { ...filters };
    const current = next[facetKey] || [];
    const updated = toggleMultiValue(current, value);
    if (updated.length) {
      next[facetKey] = updated;
    } else {
      delete next[facetKey];
    }
    onChange(next);
  }

  return (
    <aside className="filter-sidebar">
      <div className="filter-sidebar__header">
        <h2>Filters</h2>
        {activeCount > 0 && (
          <button className="link-button" onClick={() => onChange({})}>
            Clear all ({activeCount})
          </button>
        )}
      </div>
      <div className="filter-sidebar__body">
        {facets.map((facet) => {
          const facetCounts = counts[facet.key] || {};
          const selected = filters[facet.key];
          return (
            <details key={facet.key} className="facet-group" open>
              <summary>{facet.label}</summary>
              <div className="facet-values">
                {facet.values.map((v) => {
                  const count = facetCounts[v.value] || 0;
                  const isChecked = facet.multi_select
                    ? (selected || []).includes(v.value)
                    : selected === v.value;
                  return (
                    <label
                      key={v.value}
                      className={`facet-chip ${isChecked ? "facet-chip--active" : ""} ${
                        count === 0 && !isChecked ? "facet-chip--empty" : ""
                      }`}
                    >
                      <input
                        type={facet.multi_select ? "checkbox" : "radio"}
                        checked={isChecked}
                        onChange={() =>
                          facet.multi_select
                            ? setMulti(facet.key, v.value)
                            : setSingle(facet.key, v.value)
                        }
                      />
                      <span className="facet-chip__label">{v.label}</span>
                      <span className="facet-chip__count">{count}</span>
                    </label>
                  );
                })}
              </div>
            </details>
          );
        })}
      </div>
    </aside>
  );
}

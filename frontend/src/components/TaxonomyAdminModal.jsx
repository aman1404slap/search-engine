import { useState } from "react";
import { api } from "../api/client";
import Modal from "./Modal";

export default function TaxonomyAdminModal({ facets, onClose, onChanged }) {
  const [activeFacet, setActiveFacet] = useState(facets[0]?.key);
  const [newValue, setNewValue] = useState("");
  const [newLabel, setNewLabel] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const facet = facets.find((f) => f.key === activeFacet);

  async function addValue(e) {
    e.preventDefault();
    if (!newValue.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await api.addTaxonomyValue(activeFacet, {
        value: newValue.trim().toLowerCase().replace(/\s+/g, "_"),
        label: newLabel.trim() || newValue.trim(),
        order: facet.values.length,
      });
      setNewValue("");
      setNewLabel("");
      onChanged();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  async function renameValue(value, label) {
    setBusy(true);
    setError(null);
    try {
      await api.updateTaxonomyValue(activeFacet, value, { label });
      onChanged();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  async function removeValue(value) {
    if (!confirm(`Remove value "${value}" from ${facet.label}? Videos already tagged with it keep the raw value.`)) return;
    setBusy(true);
    setError(null);
    try {
      await api.deleteTaxonomyValue(activeFacet, value);
      onChanged();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal title="Taxonomy" onClose={onClose} wide>
      <div className="taxonomy-admin">
        <div className="taxonomy-admin__facets">
          {facets.map((f) => (
            <button
              key={f.key}
              className={`taxonomy-admin__facet-tab ${f.key === activeFacet ? "is-active" : ""}`}
              onClick={() => setActiveFacet(f.key)}
            >
              {f.label}
              {f.multi_select && <span className="taxonomy-admin__multi-badge">multi</span>}
            </button>
          ))}
        </div>
        <div className="taxonomy-admin__values">
          {error && <p className="form-error">{error.message}</p>}
          {facet?.values.map((v) => (
            <div key={v.value} className="taxonomy-admin__value-row">
              <code>{v.value}</code>
              <input
                type="text"
                defaultValue={v.label}
                disabled={busy}
                onBlur={(e) => e.target.value !== v.label && renameValue(v.value, e.target.value)}
              />
              <button className="link-button link-button--danger" onClick={() => removeValue(v.value)} disabled={busy}>
                Remove
              </button>
            </div>
          ))}
          <form className="taxonomy-admin__add-form" onSubmit={addValue}>
            <input
              type="text"
              placeholder="new_value_slug"
              value={newValue}
              onChange={(e) => setNewValue(e.target.value)}
              disabled={busy}
            />
            <input
              type="text"
              placeholder="Display label (optional)"
              value={newLabel}
              onChange={(e) => setNewLabel(e.target.value)}
              disabled={busy}
            />
            <button type="submit" disabled={busy || !newValue.trim()}>
              Add value
            </button>
          </form>
        </div>
      </div>
    </Modal>
  );
}

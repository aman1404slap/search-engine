import { useState } from "react";

export default function SearchBar({ onSearch, searching, initialValue = "" }) {
  const [value, setValue] = useState(initialValue);

  function submit(e) {
    e.preventDefault();
    onSearch(value.trim());
  }

  function clear() {
    setValue("");
    onSearch("");
  }

  return (
    <form className="search-bar" onSubmit={submit}>
      <svg className="search-bar__icon" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
        <path
          fill="currentColor"
          d="M15.5 14h-.79l-.28-.27a6.5 6.5 0 1 0-.7.7l.27.28v.79l5 5L20.49 19zm-6 0A4.5 4.5 0 1 1 14 9.5 4.5 4.5 0 0 1 9.5 14"
        />
      </svg>
      <input
        type="text"
        placeholder="Describe what you're looking for… e.g. “hand plugging in a cable”"
        value={value}
        onChange={(e) => setValue(e.target.value)}
      />
      {value && (
        <button type="button" className="search-bar__clear" onClick={clear} aria-label="Clear search">
          ✕
        </button>
      )}
      <button type="submit" className="search-bar__submit" disabled={searching}>
        {searching ? <span className="spinner spinner--small" /> : "Search"}
      </button>
    </form>
  );
}

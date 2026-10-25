"use client";
import { useState } from "react";
import type { CustomizeCopy } from "../../i18n/customize";
import type { MarketplaceCatalog } from "../../lib/protocol";

export function MarketplaceList({ catalog, copy, busy, onCatalog, onInstall }: {
  catalog: MarketplaceCatalog | null; copy: CustomizeCopy; busy: boolean;
  onCatalog(url: string): Promise<unknown>; onInstall(url: string): Promise<unknown>;
}) {
  const [url, setUrl] = useState(catalog?.catalog_url ?? "");
  const entries = catalog?.skills ?? [];
  return <div className="marketplace" data-testid="marketplace">
    <form className="marketplace-url" onSubmit={event => { event.preventDefault(); void onCatalog(url.trim()); }}>
      <label>{copy.catalogUrl}
        <input dir="ltr" data-testid="catalog-url" value={url} placeholder="https://host/skills.json"
          onChange={event => setUrl(event.target.value)} />
      </label>
      <button type="submit" disabled={busy || !url.trim()} data-testid="catalog-load">{busy ? copy.fetching : copy.fetch}</button>
    </form>
    {catalog?.error && <p className="error" role="alert">{copy.marketplaceError}</p>}
    {!entries.length && !catalog?.error && <p className="muted">{copy.marketplaceEmpty}</p>}
    {entries.length > 0 && <ul className="marketplace-list">
      {entries.map(entry => <li key={entry.name} data-testid={`market-${entry.name}`}>
        <div>
          <b dir="ltr">{entry.name}</b>
          <p className="muted">{entry.description}</p>
          <span className="skill-card-tags">
            {entry.command && <code dir="ltr">{entry.command}</code>}
            {entry.category && <span className="skill-badge ready">{entry.category}</span>}
          </span>
        </div>
        <button disabled={busy} onClick={() => void onInstall(entry.url)}>{copy.marketplaceEntry}</button>
      </li>)}
    </ul>}
  </div>;
}

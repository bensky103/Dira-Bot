"use client";

import { useCallback, useState } from "react";

export interface CatchCriteria {
  maxPrice: number;
  minRooms: number;
  minSqm: number;
  cities: string[];
}

export interface Filters {
  timeRange: string;
  minPrice: number;
  maxPrice: number;
  minSqm: number;
  maxSqm: number;
  rooms: number[];
  catchesOnly: boolean;
  favoritesOnly: boolean;
  cities: string[];
  catchCriteria: CatchCriteria;
}

interface SidebarProps {
  totalCount: number;
  catchCount: number;
  favoriteCount: number;
  filters: Filters;
  onFiltersChange: (filters: Filters) => void;
  onRefresh: () => void;
  lastUpdated: Date | null;
}

const TIME_OPTIONS = ["24h", "3d", "7d", "30d", "All"];
const ROOM_OPTIONS = [2, 2.5, 3, 3.5, 4];
const CITY_OPTIONS = ["תל אביב", "רמת גן", "גבעתיים"];

function Section({
  title,
  defaultOpen = true,
  children,
}: {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="section">
      <div className="section-header" onClick={() => setOpen(!open)}>
        <span className="filter-label" style={{ marginBottom: 0 }}>
          {title}
        </span>
        <span className="section-chevron">{open ? "▾" : "▸"}</span>
      </div>
      {open && <div className="section-body">{children}</div>}
    </div>
  );
}

export default function Sidebar({
  totalCount,
  catchCount,
  favoriteCount,
  filters,
  onFiltersChange,
  onRefresh,
  lastUpdated,
}: SidebarProps) {
  const setTimeRange = useCallback(
    (t: string) => onFiltersChange({ ...filters, timeRange: t }),
    [filters, onFiltersChange]
  );

  const toggleRoom = useCallback(
    (r: number) => {
      const rooms = filters.rooms.includes(r)
        ? filters.rooms.filter((x) => x !== r)
        : [...filters.rooms, r];
      onFiltersChange({ ...filters, rooms });
    },
    [filters, onFiltersChange]
  );

  const toggleCatchesOnly = useCallback(
    () =>
      onFiltersChange({ ...filters, catchesOnly: !filters.catchesOnly }),
    [filters, onFiltersChange]
  );

  const toggleFavoritesOnly = useCallback(
    () =>
      onFiltersChange({ ...filters, favoritesOnly: !filters.favoritesOnly }),
    [filters, onFiltersChange]
  );

  const toggleCity = useCallback(
    (city: string) => {
      const cities = filters.cities.includes(city)
        ? filters.cities.filter((c) => c !== city)
        : [...filters.cities, city];
      onFiltersChange({ ...filters, cities });
    },
    [filters, onFiltersChange]
  );

  const handleMinPrice = useCallback(
    (val: string) => {
      const num = parseInt(val) || 0;
      onFiltersChange({ ...filters, minPrice: num });
    },
    [filters, onFiltersChange]
  );

  const handleMaxPrice = useCallback(
    (val: string) => {
      const num = parseInt(val) || 0;
      onFiltersChange({ ...filters, maxPrice: num });
    },
    [filters, onFiltersChange]
  );

  const handleMinSqm = useCallback(
    (val: string) => {
      const num = parseInt(val) || 0;
      onFiltersChange({ ...filters, minSqm: num });
    },
    [filters, onFiltersChange]
  );

  const handleMaxSqm = useCallback(
    (val: string) => {
      const num = parseInt(val) || 0;
      onFiltersChange({ ...filters, maxSqm: num });
    },
    [filters, onFiltersChange]
  );

  const updateCatch = useCallback(
    (partial: Partial<CatchCriteria>) => {
      onFiltersChange({
        ...filters,
        catchCriteria: { ...filters.catchCriteria, ...partial },
      });
    },
    [filters, onFiltersChange]
  );

  const toggleCatchCity = useCallback(
    (city: string) => {
      const cities = filters.catchCriteria.cities.includes(city)
        ? filters.catchCriteria.cities.filter((c) => c !== city)
        : [...filters.catchCriteria.cities, city];
      updateCatch({ cities });
    },
    [filters.catchCriteria.cities, updateCatch]
  );

  const timeAgo = lastUpdated
    ? `${Math.round((Date.now() - lastUpdated.getTime()) / 60000)} min ago`
    : "never";

  return (
    <div className="sidebar">
      <h1>🏠 Dira-Bot Map</h1>

      <div className="stats">
        <div className="stat-card">
          <div className="value" style={{ color: "#3b82f6" }}>
            {totalCount}
          </div>
          <div className="label">Apartments</div>
        </div>
        <div className="stat-card">
          <div className="value" style={{ color: "#ef4444" }}>
            {catchCount}
          </div>
          <div className="label">Catches</div>
        </div>
        <div className="stat-card">
          <div className="value" style={{ color: "#fbbf24" }}>
            {favoriteCount}
          </div>
          <div className="label">Favorites</div>
        </div>
      </div>

      <Section title="Time Range">
        <div className="btn-group">
          {TIME_OPTIONS.map((t) => (
            <button
              key={t}
              className={`btn ${filters.timeRange === t ? "active" : ""}`}
              onClick={() => setTimeRange(t)}
            >
              {t}
            </button>
          ))}
        </div>
      </Section>

      <Section title="Price Range (₪)">
        <div className="price-inputs">
          <input
            type="number"
            className="price-box"
            placeholder="Min"
            value={filters.minPrice || ""}
            onChange={(e) => handleMinPrice(e.target.value)}
          />
          <span className="price-separator">—</span>
          <input
            type="number"
            className="price-box"
            placeholder="Max"
            value={filters.maxPrice || ""}
            onChange={(e) => handleMaxPrice(e.target.value)}
          />
        </div>
      </Section>

      <Section title="Size (m²)">
        <div className="price-inputs">
          <input
            type="number"
            className="price-box"
            placeholder="Min"
            value={filters.minSqm || ""}
            onChange={(e) => handleMinSqm(e.target.value)}
          />
          <span className="price-separator">—</span>
          <input
            type="number"
            className="price-box"
            placeholder="Max"
            value={filters.maxSqm || ""}
            onChange={(e) => handleMaxSqm(e.target.value)}
          />
        </div>
      </Section>

      <Section title="Rooms">
        <div className="btn-group">
          {ROOM_OPTIONS.map((r) => (
            <button
              key={r}
              className={`btn ${filters.rooms.includes(r) ? "active" : ""}`}
              onClick={() => toggleRoom(r)}
            >
              {r === 4 ? "4+" : r}
            </button>
          ))}
        </div>
      </Section>

      <div className="toggle-row">
        <span style={{ fontSize: 13 }}>🔥 Catches only</span>
        <div
          className={`toggle-switch ${filters.catchesOnly ? "on" : ""}`}
          onClick={toggleCatchesOnly}
        >
          <div className="toggle-knob" />
        </div>
      </div>

      <div className="toggle-row">
        <span style={{ fontSize: 13 }}>★ Favorites only</span>
        <div
          className={`toggle-switch ${filters.favoritesOnly ? "on" : ""}`}
          onClick={toggleFavoritesOnly}
        >
          <div className="toggle-knob" />
        </div>
      </div>

      <Section title="Cities">
        <div className="checkbox-group">
          {CITY_OPTIONS.map((city) => (
            <label key={city}>
              <input
                type="checkbox"
                checked={filters.cities.includes(city)}
                onChange={() => toggleCity(city)}
              />
              {city}
            </label>
          ))}
        </div>
      </Section>

      <Section title="🔥 Catch Criteria" defaultOpen={false}>
        <div className="catch-config">
          <div className="catch-row">
            <span className="catch-label">Max Price (₪)</span>
            <input
              type="number"
              className="price-box catch-input"
              value={filters.catchCriteria.maxPrice || ""}
              onChange={(e) =>
                updateCatch({ maxPrice: parseInt(e.target.value) || 0 })
              }
            />
          </div>
          <div className="catch-row">
            <span className="catch-label">Min Rooms</span>
            <input
              type="number"
              className="price-box catch-input"
              value={filters.catchCriteria.minRooms || ""}
              onChange={(e) =>
                updateCatch({ minRooms: parseFloat(e.target.value) || 0 })
              }
            />
          </div>
          <div className="catch-row">
            <span className="catch-label">Min Size (m²)</span>
            <input
              type="number"
              className="price-box catch-input"
              value={filters.catchCriteria.minSqm || ""}
              onChange={(e) =>
                updateCatch({ minSqm: parseInt(e.target.value) || 0 })
              }
            />
          </div>
          <div style={{ marginTop: 6 }}>
            <span className="catch-label">Cities</span>
            <div className="checkbox-group" style={{ marginTop: 4 }}>
              {CITY_OPTIONS.map((city) => (
                <label key={city}>
                  <input
                    type="checkbox"
                    checked={filters.catchCriteria.cities.includes(city)}
                    onChange={() => toggleCatchCity(city)}
                  />
                  {city}
                </label>
              ))}
            </div>
          </div>
        </div>
      </Section>

      <div style={{ marginTop: "auto" }}>
        <button className="refresh-btn" onClick={onRefresh}>
          🔄 Refresh Data
        </button>
        <div className="refresh-time">Last updated: {timeAgo}</div>
      </div>
    </div>
  );
}

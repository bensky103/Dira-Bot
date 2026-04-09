"use client";

import { useState, useCallback } from "react";

export interface Filters {
  timeRange: string;
  maxPrice: number;
  rooms: number[];
  catchesOnly: boolean;
  cities: string[];
}

interface SidebarProps {
  totalCount: number;
  catchCount: number;
  filters: Filters;
  onFiltersChange: (filters: Filters) => void;
  onRefresh: () => void;
  lastUpdated: Date | null;
}

const TIME_OPTIONS = ["24h", "3d", "7d", "30d", "All"];
const ROOM_OPTIONS = [2, 2.5, 3, 3.5, 4];
const CITY_OPTIONS = ["תל אביב", "רמת גן", "גבעתיים"];

export default function Sidebar({
  totalCount,
  catchCount,
  filters,
  onFiltersChange,
  onRefresh,
  lastUpdated,
}: SidebarProps) {
  const [maxPrice, setMaxPrice] = useState(filters.maxPrice);

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

  const toggleCity = useCallback(
    (city: string) => {
      const cities = filters.cities.includes(city)
        ? filters.cities.filter((c) => c !== city)
        : [...filters.cities, city];
      onFiltersChange({ ...filters, cities });
    },
    [filters, onFiltersChange]
  );

  const handlePriceChange = useCallback(
    (val: number) => {
      setMaxPrice(val);
      onFiltersChange({ ...filters, maxPrice: val });
    },
    [filters, onFiltersChange]
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
      </div>

      <div>
        <div className="filter-label">Time Range</div>
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
      </div>

      <div>
        <div className="filter-label">Max Price (₪)</div>
        <div className="price-range">
          <span className="price-value">0</span>
          <input
            type="range"
            min={0}
            max={10000}
            step={500}
            value={maxPrice}
            onChange={(e) => handlePriceChange(Number(e.target.value))}
          />
          <span className="price-value">
            {maxPrice === 10000 ? "10k+" : maxPrice.toLocaleString()}
          </span>
        </div>
      </div>

      <div>
        <div className="filter-label">Rooms</div>
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
      </div>

      <div className="toggle-row">
        <span style={{ fontSize: 13 }}>🔥 Catches only</span>
        <div
          className={`toggle-switch ${filters.catchesOnly ? "on" : ""}`}
          onClick={toggleCatchesOnly}
        >
          <div className="toggle-knob" />
        </div>
      </div>

      <div>
        <div className="filter-label">Cities</div>
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
      </div>

      <div style={{ marginTop: "auto" }}>
        <button className="refresh-btn" onClick={onRefresh}>
          🔄 Refresh Data
        </button>
        <div className="refresh-time">Last updated: {timeAgo}</div>
      </div>
    </div>
  );
}

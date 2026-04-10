"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import Sidebar, { type Filters } from "@/components/Sidebar";
import MapViewDynamic from "@/components/MapViewDynamic";
import type { Apartment } from "@/types/apartment";

const DEFAULT_FILTERS: Filters = {
  timeRange: "7d",
  minPrice: 0,
  maxPrice: 0,
  minSqm: 0,
  maxSqm: 0,
  rooms: [],
  catchesOnly: false,
  cities: ["תל אביב", "רמת גן", "גבעתיים"],
  catchCriteria: {
    maxPrice: 5000,
    minRooms: 2,
    minSqm: 50,
    cities: ["תל אביב"],
  },
};

function matchesCatchCriteria(
  apt: Apartment,
  criteria: Filters["catchCriteria"]
): boolean {
  if (criteria.maxPrice && apt.price > criteria.maxPrice) return false;
  if (criteria.minRooms && apt.rooms < criteria.minRooms) return false;
  if (criteria.minSqm && apt.size && apt.size < criteria.minSqm) return false;
  if (criteria.cities.length > 0 && !criteria.cities.includes(apt.city))
    return false;
  return true;
}

function getTimeThreshold(range: string): Date {
  const now = new Date();
  switch (range) {
    case "24h":
      return new Date(now.getTime() - 24 * 60 * 60 * 1000);
    case "3d":
      return new Date(now.getTime() - 3 * 24 * 60 * 60 * 1000);
    case "7d":
      return new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    case "30d":
      return new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    default:
      return new Date(0); // "All"
  }
}

export default function Home() {
  const [apartments, setApartments] = useState<Apartment[]>([]);
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async (force = false) => {
    setLoading(true);
    try {
      const url = force ? "/api/apartments?force=true" : "/api/apartments";
      const res = await fetch(url);
      if (!res.ok) throw new Error("Fetch failed");
      const data: Apartment[] = await res.json();
      setApartments(data);
      setLastUpdated(new Date());
    } catch (err) {
      console.error("Failed to fetch apartments:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Load catch config from sheet on mount
  useEffect(() => {
    fetch("/api/catch-config")
      .then((res) => res.json())
      .then((config) => {
        if (config && !config.error) {
          setFilters((prev) => ({ ...prev, catchCriteria: config }));
        }
      })
      .catch(() => {});
  }, []);

  // Save catch config to sheet when it changes
  const handleFiltersChange = useCallback(
    (newFilters: Filters) => {
      const catchChanged =
        JSON.stringify(newFilters.catchCriteria) !==
        JSON.stringify(filters.catchCriteria);
      setFilters(newFilters);
      if (catchChanged) {
        fetch("/api/catch-config", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(newFilters.catchCriteria),
        }).catch(() => {});
      }
    },
    [filters.catchCriteria]
  );

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Apply catch criteria to mark apartments as catches client-side
  const withCatchFlags = useMemo(() => {
    return apartments.map((apt) => ({
      ...apt,
      isCatch: apt.isCatch || matchesCatchCriteria(apt, filters.catchCriteria),
    }));
  }, [apartments, filters.catchCriteria]);

  const filtered = useMemo(() => {
    const threshold = getTimeThreshold(filters.timeRange);

    return withCatchFlags.filter((apt) => {
      // Time filter
      if (apt.timestamp && new Date(apt.timestamp) < threshold) return false;

      // Price filter
      if (filters.minPrice && apt.price && apt.price < filters.minPrice)
        return false;
      if (filters.maxPrice && apt.price && apt.price > filters.maxPrice)
        return false;

      // Sqm filter
      if (filters.minSqm && apt.size && apt.size < filters.minSqm)
        return false;
      if (filters.maxSqm && apt.size && apt.size > filters.maxSqm)
        return false;

      // Rooms filter (empty = all rooms)
      if (filters.rooms.length > 0) {
        const matchesRoom = filters.rooms.some((r) =>
          r === 4 ? apt.rooms >= 4 : apt.rooms === r
        );
        if (!matchesRoom) return false;
      }

      // Catches only
      if (filters.catchesOnly && !apt.isCatch) return false;

      // City filter
      if (!filters.cities.includes(apt.city)) return false;

      return true;
    });
  }, [withCatchFlags, filters]);

  const catchCount = filtered.filter((a) => a.isCatch).length;

  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className={`page ${sidebarOpen ? "sidebar-open" : "sidebar-closed"}`}>
      {sidebarOpen && (
        <Sidebar
          totalCount={filtered.length}
          catchCount={catchCount}
          filters={filters}
          onFiltersChange={handleFiltersChange}
          onRefresh={() => fetchData(true)}
          lastUpdated={lastUpdated}
        />
      )}
      <button
        className="sidebar-toggle"
        onClick={() => setSidebarOpen(!sidebarOpen)}
        title={sidebarOpen ? "Hide filters" : "Show filters"}
      >
        {sidebarOpen ? "◀" : "▶"}
      </button>
      {loading && apartments.length === 0 ? (
        <div
          style={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "#f2efe9",
            color: "#666",
            fontSize: 16,
          }}
        >
          Loading apartments...
        </div>
      ) : (
        <MapViewDynamic apartments={filtered} />
      )}
    </div>
  );
}

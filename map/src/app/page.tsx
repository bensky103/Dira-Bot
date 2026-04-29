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
  favoritesOnly: false,
  catchCriteria: {
    maxPrice: 5000,
    minRooms: 2,
    minSqm: 50,
  },
};

function matchesCatchCriteria(
  apt: Apartment,
  criteria: Filters["catchCriteria"]
): boolean {
  if (criteria.maxPrice && apt.price > criteria.maxPrice) return false;
  if (criteria.minRooms && apt.rooms < criteria.minRooms) return false;
  if (criteria.minSqm && apt.size && apt.size < criteria.minSqm) return false;
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

const FILTERS_STORAGE_KEY = "dira-bot:filters:v1";

// Persist all UI-side filters except catchCriteria (which lives in the Google Sheet Config tab).
type StoredFilters = Omit<Filters, "catchCriteria">;

function loadStoredFilters(): StoredFilters | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(FILTERS_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<StoredFilters>;
    // Defensive: ensure shape matches what we expect.
    if (!parsed || typeof parsed !== "object") return null;
    return {
      timeRange: parsed.timeRange ?? DEFAULT_FILTERS.timeRange,
      minPrice: parsed.minPrice ?? DEFAULT_FILTERS.minPrice,
      maxPrice: parsed.maxPrice ?? DEFAULT_FILTERS.maxPrice,
      minSqm: parsed.minSqm ?? DEFAULT_FILTERS.minSqm,
      maxSqm: parsed.maxSqm ?? DEFAULT_FILTERS.maxSqm,
      rooms: Array.isArray(parsed.rooms) ? parsed.rooms : DEFAULT_FILTERS.rooms,
      catchesOnly: !!parsed.catchesOnly,
      favoritesOnly: !!parsed.favoritesOnly,
    };
  } catch {
    return null;
  }
}

export default function Home() {
  const [apartments, setApartments] = useState<Apartment[]>([]);
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [filtersHydrated, setFiltersHydrated] = useState(false);
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

  // Hydrate filters from localStorage after mount (avoids SSR hydration mismatch).
  useEffect(() => {
    const stored = loadStoredFilters();
    if (stored) {
      setFilters((prev) => ({ ...stored, catchCriteria: prev.catchCriteria }));
    }
    setFiltersHydrated(true);
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

  // Persist filters to localStorage on every change (after hydration).
  useEffect(() => {
    if (!filtersHydrated) return;
    try {
      const { catchCriteria: _ignored, ...toStore } = filters;
      void _ignored;
      window.localStorage.setItem(FILTERS_STORAGE_KEY, JSON.stringify(toStore));
    } catch {
      /* localStorage may be unavailable (private mode, quota) — ignore */
    }
  }, [filters, filtersHydrated]);

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

      // Favorites only
      if (filters.favoritesOnly && !apt.isFavorite) return false;

      return true;
    });
  }, [withCatchFlags, filters]);

  const catchCount = filtered.filter((a) => a.isCatch).length;
  const favoriteCount = filtered.filter((a) => a.isFavorite).length;

  const handleDelete = useCallback(async (link: string) => {
    try {
      const res = await fetch("/api/apartments/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ link }),
      });
      if (!res.ok) throw new Error("Delete failed");
      setApartments((prev) => prev.filter((apt) => apt.link !== link));
    } catch (err) {
      console.error("Failed to delete apartment:", err);
    }
  }, []);

  const handleFavorite = useCallback(async (link: string, favorite: boolean) => {
    // Optimistic update
    setApartments((prev) =>
      prev.map((apt) =>
        apt.link === link ? { ...apt, isFavorite: favorite } : apt
      )
    );
    try {
      const res = await fetch("/api/apartments/favorite", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ link, favorite }),
      });
      if (!res.ok) throw new Error("Favorite toggle failed");
    } catch (err) {
      console.error("Failed to toggle favorite:", err);
      // Revert on error
      setApartments((prev) =>
        prev.map((apt) =>
          apt.link === link ? { ...apt, isFavorite: !favorite } : apt
        )
      );
    }
  }, []);

  const handleSeen = useCallback(async (link: string, seen: boolean) => {
    // Optimistic update
    setApartments((prev) =>
      prev.map((apt) => (apt.link === link ? { ...apt, isSeen: seen } : apt))
    );
    try {
      const res = await fetch("/api/apartments/seen", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ link, seen }),
      });
      if (!res.ok) throw new Error("Seen toggle failed");
    } catch (err) {
      console.error("Failed to toggle seen:", err);
      // Revert on error
      setApartments((prev) =>
        prev.map((apt) =>
          apt.link === link ? { ...apt, isSeen: !seen } : apt
        )
      );
    }
  }, []);

  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className={`page ${sidebarOpen ? "sidebar-open" : "sidebar-closed"}`}>
      {sidebarOpen && (
        <Sidebar
          totalCount={filtered.length}
          catchCount={catchCount}
          favoriteCount={favoriteCount}
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
        <span className="toggle-desktop">{sidebarOpen ? "◀" : "▶"}</span>
        <span className="toggle-mobile">{sidebarOpen ? "▼" : "▲"}</span>
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
        <MapViewDynamic
          apartments={filtered}
          onDelete={handleDelete}
          onFavorite={handleFavorite}
          onSeen={handleSeen}
        />
      )}
    </div>
  );
}

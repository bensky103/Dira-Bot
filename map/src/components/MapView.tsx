"use client";

import { useMemo, useState } from "react";
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Marker,
  Popup,
  useMapEvents,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { Apartment } from "@/types/apartment";
import ApartmentPopup from "./ApartmentPopup";

// Fix Leaflet default marker icon issue with bundlers
const defaultIcon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const catchIcon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
  className: "catch-marker",
});

interface AreaCluster {
  city: string;
  area: string;
  lat: number;
  lng: number;
  count: number;
  hasCatch: boolean;
  apartments: Apartment[];
}

const ZOOM_THRESHOLD = 13;

function ZoomTracker({ onZoomChange }: { onZoomChange: (z: number) => void }) {
  useMapEvents({
    zoomend: (e) => onZoomChange(e.target.getZoom()),
  });
  return null;
}

interface MapViewProps {
  apartments: Apartment[];
}

export default function MapView({ apartments }: MapViewProps) {
  const [zoom, setZoom] = useState(12);

  // Group apartments by city+area for area circles
  const clusters = useMemo(() => {
    const map = new Map<string, AreaCluster>();
    for (const apt of apartments) {
      const key = `${apt.city}|${apt.area}`;
      if (!map.has(key)) {
        map.set(key, {
          city: apt.city,
          area: apt.area,
          lat: apt.lat,
          lng: apt.lng,
          count: 0,
          hasCatch: false,
          apartments: [],
        });
      }
      const cluster = map.get(key)!;
      cluster.count++;
      if (apt.isCatch) cluster.hasCatch = true;
      cluster.apartments.push(apt);
      // Average the coordinates for better center
      cluster.lat =
        (cluster.lat * (cluster.count - 1) + apt.lat) / cluster.count;
      cluster.lng =
        (cluster.lng * (cluster.count - 1) + apt.lng) / cluster.count;
    }
    return Array.from(map.values());
  }, [apartments]);

  const showClusters = zoom <= ZOOM_THRESHOLD;

  return (
    <MapContainer
      center={[32.07, 34.79]}
      zoom={12}
      className="map-container"
      style={{ height: "100%", width: "100%" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <ZoomTracker onZoomChange={setZoom} />

      {showClusters
        ? clusters.map((cluster) => {
            const radius = Math.min(
              40,
              Math.max(15, 10 + cluster.count * 2)
            );
            const color = cluster.hasCatch ? "#ef4444" : "#3b82f6";
            return (
              <CircleMarker
                key={`${cluster.city}|${cluster.area}`}
                center={[cluster.lat, cluster.lng]}
                radius={radius}
                pathOptions={{
                  fillColor: color,
                  fillOpacity: 0.35,
                  color: color,
                  weight: 2,
                }}
              >
                <Popup>
                  <div className="popup-card">
                    <div className="popup-header">
                      <span className="area-name">
                        {cluster.area} ({cluster.city})
                      </span>
                    </div>
                    <div className="popup-details">
                      <div className="detail-row">
                        <span className="detail-label">Listings</span>
                        <span className="detail-value">{cluster.count}</span>
                      </div>
                      {cluster.hasCatch && (
                        <div className="detail-row">
                          <span className="detail-label">Catches</span>
                          <span
                            className="detail-value"
                            style={{ color: "#ef4444" }}
                          >
                            {
                              cluster.apartments.filter((a) => a.isCatch)
                                .length
                            }
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </Popup>
              </CircleMarker>
            );
          })
        : apartments.map((apt, i) => (
            <Marker
              key={`${apt.link}-${i}`}
              position={[apt.lat, apt.lng]}
              icon={apt.isCatch ? catchIcon : defaultIcon}
            >
              <Popup>
                <ApartmentPopup apartment={apt} />
              </Popup>
            </Marker>
          ))}
    </MapContainer>
  );
}

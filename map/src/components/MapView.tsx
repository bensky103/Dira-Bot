"use client";

import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  useMap,
} from "react-leaflet";
import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { Apartment } from "@/types/apartment";
import ApartmentPopup from "./ApartmentPopup";

function PopupAutoSize({ children }: { children: React.ReactNode }) {
  const map = useMap();
  const popupRef = useRef<L.Popup | null>(null);

  useEffect(() => {
    // After React renders content, tell Leaflet to recalculate size
    const onOpen = () => {
      setTimeout(() => {
        if (popupRef.current) {
          popupRef.current.update();
        }
      }, 0);
    };
    map.on("popupopen", onOpen);
    return () => { map.off("popupopen", onOpen); };
  }, [map]);

  return (
    <Popup ref={popupRef} minWidth={260} maxWidth={300}>
      {children}
    </Popup>
  );
}

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

const favoriteIcon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
  className: "favorite-marker",
});

const seenIcon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
  className: "seen-marker",
});

interface MapViewProps {
  apartments: Apartment[];
  onDelete?: (link: string) => void;
  onFavorite?: (link: string, favorite: boolean) => void;
  onSeen?: (link: string, seen: boolean) => void;
}

function pickIcon(apt: Apartment): L.Icon {
  // Favorite always wins (most important state to surface)
  if (apt.isFavorite) return favoriteIcon;
  // Seen greys out everything else
  if (apt.isSeen) return seenIcon;
  if (apt.isCatch) return catchIcon;
  return defaultIcon;
}

export default function MapView({ apartments, onDelete, onFavorite, onSeen }: MapViewProps) {
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

      {apartments.map((apt, i) => (
        <Marker
          key={`${apt.link}-${i}`}
          position={[apt.lat, apt.lng]}
          icon={pickIcon(apt)}
          eventHandlers={{
            click: () => {
              if (!apt.isSeen) onSeen?.(apt.link, true);
            },
          }}
        >
          <PopupAutoSize>
            <ApartmentPopup
              apartment={apt}
              onDelete={onDelete}
              onFavorite={onFavorite}
              onSeen={onSeen}
            />
          </PopupAutoSize>
        </Marker>
      ))}
    </MapContainer>
  );
}

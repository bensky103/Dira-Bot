"use client";

import dynamic from "next/dynamic";
import type { Apartment } from "@/types/apartment";

const MapView = dynamic(() => import("./MapView"), {
  ssr: false,
  loading: () => (
    <div
      style={{
        flex: 1,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#f2efe9",
        color: "#666",
      }}
    >
      Loading map...
    </div>
  ),
});

export default function MapViewDynamic({
  apartments,
  onDelete,
  onFavorite,
}: {
  apartments: Apartment[];
  onDelete?: (link: string) => void;
  onFavorite?: (link: string, favorite: boolean) => void;
}) {
  return <MapView apartments={apartments} onDelete={onDelete} onFavorite={onFavorite} />;
}

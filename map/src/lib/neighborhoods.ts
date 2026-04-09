interface Coords {
  lat: number;
  lng: number;
}

const NEIGHBORHOODS: Record<string, Record<string, Coords>> = {
  "תל אביב": {
    "צפון ישן": { lat: 32.0853, lng: 34.7818 },
    "הצפון החדש": { lat: 32.0900, lng: 34.7820 },
    "לב העיר": { lat: 32.0700, lng: 34.7750 },
    "פלורנטין": { lat: 32.0560, lng: 34.7700 },
    "נווה צדק": { lat: 32.0590, lng: 34.7650 },
    "יד אליהו": { lat: 32.0550, lng: 34.7950 },
    "נווה שאנן": { lat: 32.0530, lng: 34.7780 },
    "כרם התימנים": { lat: 32.0680, lng: 34.7660 },
    "שפירא": { lat: 32.0500, lng: 34.7720 },
    "צפון תל אביב": { lat: 32.1050, lng: 34.7900 },
    "הדר יוסף": { lat: 32.1020, lng: 34.8050 },
    "בבלי": { lat: 32.0950, lng: 34.7850 },
    "לב תל אביב": { lat: 32.0750, lng: 34.7800 },
    "מונטיפיורי": { lat: 32.0620, lng: 34.7710 },
    "יפו": { lat: 32.0450, lng: 34.7560 },
  },
  "רמת גן": {
    "מרכז": { lat: 32.0680, lng: 34.8130 },
    "גבול גבעתיים": { lat: 32.0650, lng: 34.8050 },
    "רמת חן": { lat: 32.0850, lng: 34.8100 },
    "תל בנימין": { lat: 32.0780, lng: 34.8200 },
    "נווה יהושע": { lat: 32.0750, lng: 34.8150 },
  },
  "גבעתיים": {
    "מרכז": { lat: 32.0710, lng: 34.8100 },
    "בורוכוב": { lat: 32.0740, lng: 34.8050 },
    "רמת עמידר": { lat: 32.0680, lng: 34.8070 },
  },
};

const CITY_CENTERS: Record<string, Coords> = {
  "תל אביב": { lat: 32.0750, lng: 34.7800 },
  "רמת גן": { lat: 32.0700, lng: 34.8130 },
  "גבעתיים": { lat: 32.0710, lng: 34.8100 },
};

export function getNeighborhoodCoords(
  city: string,
  area: string
): Coords | null {
  return NEIGHBORHOODS[city]?.[area] ?? CITY_CENTERS[city] ?? null;
}

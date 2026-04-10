const GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json";

// Cache reverse-geocode results per coordinate pair
const reverseCache = new Map<string, string | null>();

// Canonical city name mapping — Google may return different spellings
const CITY_ALIASES: Record<string, string> = {
  "תל אביב-יפו": "תל אביב",
  "תל אביב יפו": "תל אביב",
  "Tel Aviv-Yafo": "תל אביב",
  "Tel Aviv": "תל אביב",
  "Ramat Gan": "רמת גן",
  "Givatayim": "גבעתיים",
};

/**
 * Reverse-geocode coordinates to extract the actual city name.
 * Returns the Hebrew city name, or null if it can't be determined.
 */
export async function reverseGeocodeCity(
  lat: number,
  lng: number
): Promise<string | null> {
  const apiKey = process.env.GOOGLE_MAPS_API_KEY;
  if (!apiKey) return null;

  const cacheKey = `${lat.toFixed(5)},${lng.toFixed(5)}`;
  if (reverseCache.has(cacheKey)) {
    return reverseCache.get(cacheKey)!;
  }

  try {
    const params = new URLSearchParams({
      latlng: `${lat},${lng}`,
      key: apiKey,
      language: "he",
      result_type: "locality",
    });

    const resp = await fetch(`${GEOCODE_URL}?${params}`);
    const data = await resp.json();

    if (data.status !== "OK" || !data.results?.length) {
      reverseCache.set(cacheKey, null);
      return null;
    }

    const components = data.results[0].address_components ?? [];
    for (const comp of components) {
      if (comp.types?.includes("locality")) {
        const raw: string = comp.long_name;
        const city = CITY_ALIASES[raw] ?? raw;
        reverseCache.set(cacheKey, city);
        return city;
      }
    }

    reverseCache.set(cacheKey, null);
    return null;
  } catch {
    reverseCache.set(cacheKey, null);
    return null;
  }
}

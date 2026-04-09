const GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json";

// In-memory cache for geocoded coordinates (lives per serverless invocation)
const geocodeCache = new Map<string, { lat: number; lng: number } | null>();

export async function geocodeAddress(
  street: string,
  city: string
): Promise<{ lat: number; lng: number } | null> {
  const apiKey = process.env.GOOGLE_MAPS_API_KEY;
  if (!apiKey || !street || !city) {
    return null;
  }

  const cacheKey = `${street}|${city}`;
  if (geocodeCache.has(cacheKey)) {
    return geocodeCache.get(cacheKey)!;
  }

  try {
    const query = `${street}, ${city}, ישראל`;
    const params = new URLSearchParams({
      address: query,
      key: apiKey,
      language: "he",
      region: "il",
    });

    const resp = await fetch(`${GEOCODE_URL}?${params}`);
    const data = await resp.json();

    if (data.status !== "OK" || !data.results?.length) {
      geocodeCache.set(cacheKey, null);
      return null;
    }

    const location = data.results[0].geometry.location;
    const coords = { lat: location.lat, lng: location.lng };
    geocodeCache.set(cacheKey, coords);
    return coords;
  } catch {
    geocodeCache.set(cacheKey, null);
    return null;
  }
}

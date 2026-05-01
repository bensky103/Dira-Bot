export interface Apartment {
  timestamp: string;
  city: string;
  area: string;
  street: string;
  price: number;
  rooms: number;
  size: number;
  phone: string;
  link: string;
  isCatch: boolean;
  isFavorite: boolean;
  isSeen: boolean;
  lat: number;
  lng: number;
  // Lightweight flags for the list payload. Full description + image URLs
  // are fetched on demand via /api/apartments/details when a popup opens.
  hasDescription: boolean;
  imageCount: number;
}

export interface ApartmentDetails {
  description: string;
  images: string[];
}

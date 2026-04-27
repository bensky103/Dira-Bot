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
  description: string;
  lat: number;
  lng: number;
  images: string[];
}

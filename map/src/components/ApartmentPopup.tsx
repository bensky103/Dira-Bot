import type { Apartment } from "@/types/apartment";

interface ApartmentPopupProps {
  apartment: Apartment;
}

export default function ApartmentPopup({ apartment }: ApartmentPopupProps) {
  return (
    <div className="popup-card">
      <div className="popup-header">
        <span className="area-name">{apartment.area}</span>
        {apartment.isCatch && <span className="catch-badge">🔥 CATCH</span>}
      </div>
      <div className="popup-details">
        <div className="detail-row">
          <span className="detail-label">Price</span>
          <span className="detail-value">
            ₪{apartment.price.toLocaleString()}
          </span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Rooms</span>
          <span className="detail-value">{apartment.rooms}</span>
        </div>
        {apartment.size > 0 && (
          <div className="detail-row">
            <span className="detail-label">Size</span>
            <span className="detail-value">{apartment.size} sqm</span>
          </div>
        )}
      </div>
      <a
        className="popup-link"
        href={apartment.link}
        target="_blank"
        rel="noopener noreferrer"
      >
        View Post →
      </a>
    </div>
  );
}

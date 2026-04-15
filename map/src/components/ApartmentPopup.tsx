import { useState } from "react";
import type { Apartment } from "@/types/apartment";

interface ApartmentPopupProps {
  apartment: Apartment;
  onDelete?: (link: string) => void;
  onFavorite?: (link: string, favorite: boolean) => void;
}

function ImageCarousel({ images }: { images: string[] }) {
  const [index, setIndex] = useState(0);

  return (
    <div className="popup-carousel">
      <div
        className="carousel-track"
        style={{ transform: `translateX(-${index * 100}%)` }}
      >
        {images.map((src, i) => (
          <img key={i} src={src} alt={`Photo ${i + 1}`} className="carousel-img" />
        ))}
      </div>
      {images.length > 1 && (
        <>
          <button
            className="carousel-btn carousel-prev"
            onClick={(e) => { e.stopPropagation(); setIndex((index - 1 + images.length) % images.length); }}
          >
            ‹
          </button>
          <button
            className="carousel-btn carousel-next"
            onClick={(e) => { e.stopPropagation(); setIndex((index + 1) % images.length); }}
          >
            ›
          </button>
          <div className="carousel-dots">
            {images.map((_, i) => (
              <span
                key={i}
                className={`carousel-dot ${i === index ? "active" : ""}`}
                onClick={(e) => { e.stopPropagation(); setIndex(i); }}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export default function ApartmentPopup({ apartment, onDelete, onFavorite }: ApartmentPopupProps) {
  const [deleting, setDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [toggling, setToggling] = useState(false);

  const handleDelete = () => {
    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }
    setDeleting(true);
    onDelete?.(apartment.link);
  };

  const handleFavorite = async () => {
    setToggling(true);
    onFavorite?.(apartment.link, !apartment.isFavorite);
    setToggling(false);
  };

  return (
    <div className="popup-card">
      {apartment.images.length > 0 && (
        <ImageCarousel images={apartment.images} />
      )}
      <div className="popup-header">
        <span className="area-name">{apartment.area}</span>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          {apartment.isCatch && <span className="catch-badge">🔥 CATCH</span>}
          <button
            className={`favorite-btn ${apartment.isFavorite ? "active" : ""}`}
            onClick={handleFavorite}
            disabled={toggling}
            title={apartment.isFavorite ? "Remove from favorites" : "Add to favorites"}
          >
            ★
          </button>
        </div>
      </div>
      {apartment.street && (
        <div className="popup-street">{apartment.street}</div>
      )}
      <div className="popup-details">
        <div className="detail-row">
          <span className="detail-label">Price</span>
          <span className="detail-value price">
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
            <span className="detail-value">{apartment.size} m²</span>
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
      {onDelete && (
        <button
          className={`popup-delete ${confirmDelete ? "confirm" : ""}`}
          onClick={handleDelete}
          disabled={deleting}
        >
          {deleting ? "Deleting..." : confirmDelete ? "Click again to confirm" : "Delete"}
        </button>
      )}
    </div>
  );
}

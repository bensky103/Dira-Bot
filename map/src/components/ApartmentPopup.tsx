import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import type { Apartment } from "@/types/apartment";

interface ApartmentPopupProps {
  apartment: Apartment;
  onDelete?: (link: string) => void;
  onFavorite?: (link: string, favorite: boolean) => void;
  onSeen?: (link: string, seen: boolean) => void;
}

function Lightbox({
  images,
  startIndex,
  onClose,
}: {
  images: string[];
  startIndex: number;
  onClose: () => void;
}) {
  const [index, setIndex] = useState(startIndex);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      else if (e.key === "ArrowLeft")
        setIndex((i) => (i - 1 + images.length) % images.length);
      else if (e.key === "ArrowRight")
        setIndex((i) => (i + 1) % images.length);
    };
    window.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [images.length, onClose]);

  // Portal to <body> so the overlay escapes Leaflet popup's transform context,
  // which otherwise breaks `position: fixed` (it would be fixed to the popup).
  if (!mounted) return null;

  const overlay = (
    <div className="lightbox-overlay" onClick={onClose}>
      <button
        className="lightbox-close"
        onClick={(e) => {
          e.stopPropagation();
          onClose();
        }}
        aria-label="Close"
      >
        ×
      </button>
      <img
        src={images[index]}
        alt={`Photo ${index + 1}`}
        className="lightbox-img"
        onClick={(e) => e.stopPropagation()}
      />
      {images.length > 1 && (
        <>
          <button
            className="lightbox-btn lightbox-prev"
            onClick={(e) => {
              e.stopPropagation();
              setIndex((index - 1 + images.length) % images.length);
            }}
            aria-label="Previous"
          >
            ‹
          </button>
          <button
            className="lightbox-btn lightbox-next"
            onClick={(e) => {
              e.stopPropagation();
              setIndex((index + 1) % images.length);
            }}
            aria-label="Next"
          >
            ›
          </button>
          <div className="lightbox-counter">
            {index + 1} / {images.length}
          </div>
        </>
      )}
    </div>
  );

  return createPortal(overlay, document.body);
}

function ImageCarousel({
  images,
  onOpenLightbox,
}: {
  images: string[];
  onOpenLightbox: (index: number) => void;
}) {
  const [index, setIndex] = useState(0);

  return (
    <div className="popup-carousel">
      <div
        className="carousel-track"
        style={{ transform: `translateX(-${index * 100}%)` }}
      >
        {images.map((src, i) => (
          <img
            key={i}
            src={src}
            alt={`Photo ${i + 1}`}
            className="carousel-img"
            style={{ cursor: "zoom-in" }}
            onClick={(e) => {
              e.stopPropagation();
              onOpenLightbox(i);
            }}
          />
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

export default function ApartmentPopup({ apartment, onDelete, onFavorite, onSeen }: ApartmentPopupProps) {
  const [deleting, setDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [toggling, setToggling] = useState(false);
  const [descriptionOpen, setDescriptionOpen] = useState(false);
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

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

  const handleUnsee = () => {
    onSeen?.(apartment.link, false);
  };

  const hasDescription =
    apartment.description && apartment.description.trim().length > 0;

  return (
    <div className="popup-card">
      {apartment.images.length > 0 && (
        <ImageCarousel
          images={apartment.images}
          onOpenLightbox={(i) => setLightboxIndex(i)}
        />
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
        {apartment.timestamp && (
          <div className="detail-row">
            <span className="detail-label">Added</span>
            <span className="detail-value">
              {(() => {
                const d = new Date(apartment.timestamp);
                const dd = String(d.getDate()).padStart(2, "0");
                const mm = String(d.getMonth() + 1).padStart(2, "0");
                const yy = String(d.getFullYear()).slice(-2);
                return `${dd}/${mm}/${yy}`;
              })()}
            </span>
          </div>
        )}
      </div>
      {hasDescription && (
        <div className="popup-description">
          <button
            className="description-toggle"
            onClick={(e) => {
              e.stopPropagation();
              setDescriptionOpen((o) => !o);
            }}
          >
            {descriptionOpen ? "▼" : "▶"} Full post details
          </button>
          {descriptionOpen && (
            <div className="description-body" dir="auto">
              {apartment.description}
            </div>
          )}
        </div>
      )}
      <a
        className="popup-link"
        href={apartment.link}
        target="_blank"
        rel="noopener noreferrer"
      >
        View Post →
      </a>
      {apartment.isSeen && onSeen && (
        <button
          className="popup-unsee"
          onClick={handleUnsee}
          title="Mark as unseen"
        >
          Mark as unseen
        </button>
      )}
      {onDelete && (
        <button
          className={`popup-delete ${confirmDelete ? "confirm" : ""}`}
          onClick={handleDelete}
          disabled={deleting}
        >
          {deleting ? "Deleting..." : confirmDelete ? "Click again to confirm" : "Delete"}
        </button>
      )}
      {lightboxIndex !== null && (
        <Lightbox
          images={apartment.images}
          startIndex={lightboxIndex}
          onClose={() => setLightboxIndex(null)}
        />
      )}
    </div>
  );
}

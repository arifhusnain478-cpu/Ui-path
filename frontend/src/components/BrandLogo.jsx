import { useState } from "react";

const logo_sources = {
  full: "/brand/full-logo.png",
  short: "/brand/short-logo.png",
};

const logo_classes = {
  full: "h-12 w-auto max-w-[200px] sm:h-14 sm:max-w-[240px]",
  short: "h-8 w-8",
  hero: "h-14 w-auto max-w-[220px] sm:h-16 sm:max-w-[280px]",
};

export default function BrandLogo({
  variant = "short",
  alt = "QualiTrace AI",
  className = "",
  fallbackClassName = "",
}) {
  const [has_error, setHasError] = useState(false);
  const src = logo_sources[variant === "short" ? "short" : "full"];
  const size_class = logo_classes[variant] || logo_classes.short;

  if (has_error) {
    return (
      <span
        className={`inline-flex items-center font-medium tracking-tight text-[var(--qt-text-primary)] ${fallbackClassName}`}
      >
        QualiTrace AI
      </span>
    );
  }

  return (
    <img
      src={src}
      alt={alt}
      className={`${size_class} object-contain ${className}`}
      onError={() => setHasError(true)}
    />
  );
}
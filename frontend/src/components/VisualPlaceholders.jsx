function VisualPlaceholder({ label, variant = "hero" }) {
  const min_height =
    variant === "review" ? "min-h-[220px]" : variant === "case" ? "min-h-[200px]" : "min-h-[260px]";

  return (
    <figure
      className={`qt-visual-placeholder relative flex ${min_height} items-end`}
      aria-label={`${label} visual placeholder`}
    >
      <figcaption className="absolute bottom-3 left-3 z-10 text-[10px] font-medium uppercase tracking-wider text-[var(--qt-text-muted)]">
        {label}
      </figcaption>
    </figure>
  );
}

export function HeroVisualPlaceholder() {
  return (
    <figure className="qt-visual-placeholder relative min-h-[260px] overflow-hidden">
      <img
        src="/visuals/dashboard-visual.png"
        alt="Pharmaceutical quality professional in a laboratory environment"
        className="h-full w-full object-cover"
      />
    </figure>
  );
}

export function CaseVisualPlaceholder({ risk_level, product_name }) {
  const is_critical = risk_level === "critical";
  const is_medicine_case =
    product_name &&
    (product_name.toLowerCase().includes("metformin") ||
      product_name.toLowerCase().includes("tablet") ||
      product_name.toLowerCase().includes("capsule") ||
      product_name.toLowerCase().includes("mg"));

  if (is_critical) {
    return (
      <figure className="qt-visual-placeholder relative min-h-[200px] overflow-hidden">
        <img
          src="/visuals/critical-case-visual.png"
          alt="Sterile pharmaceutical vial under laboratory inspection"
          className="h-full w-full object-cover"
        />
      </figure>
    );
  }

  if (is_medicine_case) {
    return (
      <figure className="qt-visual-placeholder relative min-h-[200px] overflow-hidden">
        <img
          src="/visuals/medicine-case-visual.png"
          alt="Pharmaceutical quality inspection in a controlled laboratory"
          className="h-full w-full object-cover"
        />
      </figure>
    );
  }

  return (
    <VisualPlaceholder
      label="Visual"
      variant="case"
    />
  );
}

export function ReviewVisualPlaceholder() {
  return (
    <VisualPlaceholder
      label="Visual"
      variant="review"
    />
  );
}
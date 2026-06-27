export function formatSnakeCaseLabel(value) {
  if (value === null || value === undefined || value === "") {
    return "Not provided";
  }

  return String(value)
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function formatRoleLabel(value) {
  return formatSnakeCaseLabel(value);
}

export function formatStatusLabel(value) {
  return formatSnakeCaseLabel(value);
}

export function formatComplaintTypeLabel(value) {
  return formatSnakeCaseLabel(value);
}

export function formatDateTime(value) {
  if (!value) {
    return "Not provided";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function formatDate(value) {
  if (!value) {
    return "Not provided";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
  }).format(date);
}

export function displayValue(value) {
  if (value === null || value === undefined || value === "") {
    return "Not provided";
  }

  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }

  return String(value);
}

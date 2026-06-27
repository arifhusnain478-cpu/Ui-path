import apiClient from "./client.js";
import {
  CASE_STATUSES,
  COMPLAINT_TYPES,
  JURISDICTIONS,
  RISK_LEVELS,
} from "../config/constants.js";

const create_statuses = CASE_STATUSES.filter((status) =>
  ["open", "pending_review"].includes(status),
);

function normalizeCaseListResponse(data) {
  if (Array.isArray(data)) {
    return data;
  }

  if (data && typeof data === "object") {
    if (Array.isArray(data.cases)) {
      return data.cases;
    }

    if (Array.isArray(data.complaints)) {
      return data.complaints;
    }

    if (Array.isArray(data.data)) {
      return data.data;
    }
  }

  throw new Error("GET /complaints response did not match the documented contract.");
}

function normalizeAuditTrailResponse(data, route_case_id) {
  let events;

  if (Array.isArray(data)) {
    events = data;
  } else if (data && typeof data === "object") {
    if (Array.isArray(data.audit)) {
      events = data.audit;
    } else if (Array.isArray(data.events)) {
      events = data.events;
    } else if (Array.isArray(data.data)) {
      events = data.data;
    }
  }

  if (!Array.isArray(events)) {
    throw new Error("GET /cases/{case_id}/audit response did not match the documented contract.");
  }

  const invalid_event = events.find((event) => {
    if (!event || typeof event !== "object" || Array.isArray(event)) {
      return true;
    }

    if (event.timestamp !== undefined && (typeof event.timestamp !== "string" || event.timestamp.trim().length === 0)) {
      return true;
    }

    if (event.case_id !== undefined && event.case_id !== route_case_id) {
      return true;
    }

    return false;
  });

  if (invalid_event) {
    throw new Error("GET /cases/{case_id}/audit response included a malformed event.");
  }

  return events;
}

function validateCaseResponse(data) {
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    throw new Error("GET /complaints/{case_id} response did not match the documented contract.");
  }

  if (typeof data.case_id !== "string" || data.case_id.trim().length === 0) {
    throw new Error("GET /complaints/{case_id} response did not include case_id.");
  }

  if (data.jurisdiction !== undefined && !JURISDICTIONS.includes(data.jurisdiction)) {
    throw new Error("GET /complaints/{case_id} response included invalid jurisdiction.");
  }

  if (data.risk_level !== undefined && !RISK_LEVELS.includes(data.risk_level)) {
    throw new Error("GET /complaints/{case_id} response included invalid risk_level.");
  }

  if (data.status !== undefined && !CASE_STATUSES.includes(data.status)) {
    throw new Error("GET /complaints/{case_id} response included invalid status.");
  }

  if (
    data.product_name !== undefined &&
    typeof data.product_name !== "string"
  ) {
    throw new Error("GET /complaints/{case_id} response included invalid product_name.");
  }

  if (
    data.batch_number !== undefined &&
    data.batch_number !== null &&
    typeof data.batch_number !== "string"
  ) {
    throw new Error("GET /complaints/{case_id} response included invalid batch_number.");
  }

  if (
    data.complaint_type !== undefined &&
    !COMPLAINT_TYPES.includes(data.complaint_type)
  ) {
    throw new Error("GET /complaints/{case_id} response included invalid complaint_type.");
  }

  if (
    data.confidence_score !== undefined &&
    (typeof data.confidence_score !== "number" ||
      data.confidence_score < 0 ||
      data.confidence_score > 1)
  ) {
    throw new Error("GET /complaints/{case_id} response included invalid confidence_score.");
  }

  if (
    data.source_list !== undefined &&
    (!Array.isArray(data.source_list) ||
      data.source_list.some((source) => typeof source !== "string"))
  ) {
    throw new Error("GET /complaints/{case_id} response included invalid source_list.");
  }

  if (data.created_at !== undefined && typeof data.created_at !== "string") {
    throw new Error("GET /complaints/{case_id} response included invalid created_at.");
  }

  if (data.updated_at !== undefined && typeof data.updated_at !== "string") {
    throw new Error("GET /complaints/{case_id} response included invalid updated_at.");
  }

  if (
    data.patient_impact !== undefined &&
    typeof data.patient_impact !== "boolean"
  ) {
    throw new Error("GET /complaints/{case_id} response included invalid patient_impact.");
  }

  if (
    data.current_stage !== undefined &&
    typeof data.current_stage !== "string"
  ) {
    throw new Error("GET /complaints/{case_id} response included invalid current_stage.");
  }

  if (
    data.sla_deadline !== undefined &&
    data.sla_deadline !== null &&
    typeof data.sla_deadline !== "string"
  ) {
    throw new Error("GET /complaints/{case_id} response included invalid sla_deadline.");
  }

  return data;
}

export async function getCases(params = {}) {
  const response = await apiClient.get("/complaints", { params });
  return normalizeCaseListResponse(response.data);
}

export async function getCase(case_id) {
  const response = await apiClient.get(`/complaints/${case_id}`);
  return validateCaseResponse(response.data);
}

export async function createComplaint(payload) {
  const request_payload = {
    product_name: payload.product_name,
    batch_number: payload.batch_number,
    market_code: payload.market_code,
    complaint_type: payload.complaint_type,
    patient_impact: payload.patient_impact,
    description: payload.description,
  };
  const response = await apiClient.post("/complaints", request_payload);
  return validateComplaintCreateResponse(response.data);
}

function validateComplaintCreateResponse(data) {
  const is_valid =
    data &&
    typeof data === "object" &&
    !Array.isArray(data) &&
    typeof data.case_id === "string" &&
    data.case_id.trim().length > 0 &&
    JURISDICTIONS.includes(data.jurisdiction) &&
    RISK_LEVELS.includes(data.risk_level) &&
    create_statuses.includes(data.status) &&
    typeof data.confidence_score === "number" &&
    data.confidence_score >= 0 &&
    data.confidence_score <= 1 &&
    typeof data.created_at === "string" &&
    data.created_at.trim().length > 0;

  if (!is_valid) {
    throw new Error(
      "POST /complaints response did not match the documented contract.",
    );
  }

  return data;
}

export async function updateCaseStatus(case_id, payload) {
  const response = await apiClient.put(`/cases/${case_id}/status`, payload);
  return response.data;
}

export async function getAuditTrail(case_id) {
  const response = await apiClient.get(`/cases/${case_id}/audit`);
  return normalizeAuditTrailResponse(response.data, case_id);
}

export async function getCaseReport(case_id) {
  const response = await apiClient.get(`/reports/${case_id}`, {
    responseType: "blob",
  });
  return response.data;
}

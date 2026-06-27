import apiClient from "./client.js";
import { TASK_DECISIONS } from "../config/constants.js";

function normalizeTaskListResponse(data) {
  if (Array.isArray(data)) {
    return data;
  }

  if (data && typeof data === "object") {
    if (Array.isArray(data.tasks)) {
      return data.tasks;
    }

    if (Array.isArray(data.data)) {
      return data.data;
    }
  }

  throw new Error("GET /tasks response did not match the documented contract.");
}

function validateDecisionPayload(payload) {
  if (!TASK_DECISIONS.includes(payload?.decision)) {
    throw new Error("Task completion decision is not approved by the contract.");
  }

  if (
    payload.decision === "approve" &&
    payload.override_reason !== null
  ) {
    throw new Error("Approve must send override_reason as null.");
  }

  if (
    (payload.decision === "reject" || payload.decision === "override") &&
    (typeof payload.override_reason !== "string" ||
      payload.override_reason.trim().length === 0)
  ) {
    throw new Error("Reject and override require override_reason.");
  }
}

function normalizeCompletionResponse(data) {
  if (data === undefined || data === null || data === "") {
    return null;
  }

  if (data && typeof data === "object" && !Array.isArray(data)) {
    return data;
  }

  throw new Error("PUT /tasks/{task_id}/complete response did not match the documented contract.");
}

export async function getTasks(case_id) {
  const response = await apiClient.get("/tasks", { params: { case_id } });
  return normalizeTaskListResponse(response.data);
}

export async function completeTask(task_id, payload) {
  validateDecisionPayload(payload);

  const request_payload = {
    decision: payload.decision,
    override_reason: payload.override_reason,
  };
  const response = await apiClient.put(
    `/tasks/${task_id}/complete`,
    request_payload,
  );
  return normalizeCompletionResponse(response.data);
}

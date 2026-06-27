import apiClient from "./client.js";

function normalizeLoginResponse(data) {
  if (data?.token && data?.user) {
    return {
      token: data.token,
      user: data.user,
    };
  }

  if (data?.token && data?.user_id && data?.role) {
    return {
      token: data.token,
      user: {
        user_id: data.user_id,
        role: data.role,
      },
    };
  }

  throw new Error("Login response did not match the documented contract.");
}

export async function login(payload) {
  const response = await apiClient.post("/auth/login", payload);
  return normalizeLoginResponse(response.data);
}

export async function register(payload) {
  const response = await apiClient.post("/auth/register", payload);
  return response.data;
}

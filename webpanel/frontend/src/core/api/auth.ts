import { apiRequest } from "./client";

interface MessageResponse {
  message: string;
}

export function changePassword(token: string, currentPassword: string, newPassword: string) {
  return apiRequest<MessageResponse>("/api/core/auth/password", {
    method: "POST",
    token,
    body: {
      current_password: currentPassword,
      new_password: newPassword,
    },
  });
}

import { apiRequest } from "./client";

export interface NotificationItem {
  id: number;
  title: string;
  message: string;
  status: string;
  severity: string;
  created_at: string;
  updated_at: string;
}

export interface NotificationList {
  items: NotificationItem[];
  unread_count: number;
  total: number;
  limit: number;
  offset: number;
}

export function listNotifications(token: string, limit = 20) {
  return apiRequest<NotificationList>(`/api/core/notifications?limit=${limit}`, { token });
}

export function markNotificationRead(token: string, id: number) {
  return apiRequest<NotificationItem>(`/api/core/notifications/${id}/read`, {
    method: "PATCH",
    token,
  });
}

export function markAllNotificationsRead(token: string) {
  return apiRequest<NotificationList>("/api/core/notifications/read-all", {
    method: "PATCH",
    token,
  });
}

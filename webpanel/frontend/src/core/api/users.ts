import { apiRequest } from "./client";

export interface RoleItem {
  slug: string;
  name: string;
}

export interface ManagedUser {
  id: number;
  email: string;
  display_name: string;
  is_active: boolean;
  is_superuser: boolean;
  roles: string[];
}

export interface UserCreatePayload {
  email: string;
  display_name: string;
  password: string;
  role_slugs: string[];
  is_active: boolean;
}

export function listRoles(token: string) {
  return apiRequest<RoleItem[]>("/api/core/admin/roles", { token });
}

export function listUsers(token: string) {
  return apiRequest<ManagedUser[]>("/api/core/admin/users", { token });
}

export function createUser(token: string, body: UserCreatePayload) {
  return apiRequest<ManagedUser>("/api/core/admin/users", {
    method: "POST",
    token,
    body,
  });
}

export function updateUserActiveStatus(token: string, id: number, isActive: boolean) {
  return apiRequest<ManagedUser>(`/api/core/admin/users/${id}/active`, {
    method: "PATCH",
    token,
    body: { is_active: isActive },
  });
}

export function updateUserRoles(token: string, id: number, roleSlugs: string[]) {
  return apiRequest<ManagedUser>(`/api/core/admin/users/${id}/roles`, {
    method: "PATCH",
    token,
    body: { role_slugs: roleSlugs },
  });
}

export function resetUserPassword(token: string, id: number, password: string) {
  return apiRequest<ManagedUser>(`/api/core/admin/users/${id}/password`, {
    method: "PATCH",
    token,
    body: { password },
  });
}

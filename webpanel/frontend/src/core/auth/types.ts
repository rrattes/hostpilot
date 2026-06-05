export interface CurrentUser {
  id: number;
  email: string;
  display_name: string;
  is_active: boolean;
  is_superuser: boolean;
}

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
}

export interface CurrentAccess {
  roles: string[];
  permissions: string[];
}

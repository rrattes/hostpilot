import { KeyRound, ShieldCheck, Users } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { listRoles, type RoleItem } from "../core/api/users";
import { useAuth } from "../core/auth/AuthProvider";

const CORE_ROLE_ORDER = ["admin", "operator", "viewer"];

export function RolesPage() {
  const { token } = useAuth();
  const [roles, setRoles] = useState<RoleItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const totalPermissions = useMemo(
    () => new Set(roles.flatMap((role) => role.permissions)).size,
    [roles],
  );

  useEffect(() => {
    if (!token) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    listRoles(token)
      .then((response) => {
        setRoles(sortRoles(response.map(normalizeRole)));
        setError(null);
      })
      .catch(() => {
        setRoles([]);
        setError("Unable to load roles and permissions.");
      })
      .finally(() => setIsLoading(false));
  }, [token]);

  return (
    <section className="data-page" aria-label="Roles and permissions">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Core administration</span>
          <h2>Roles & Permissions</h2>
        </div>
        <div className="page-actions">
          <span className="count-pill">
            <ShieldCheck size={14} />
            {roles.length} roles
          </span>
          <span className="count-pill">
            <KeyRound size={14} />
            {totalPermissions} permissions
          </span>
        </div>
      </div>

      {error ? <div className="login-error">{error}</div> : null}

      <div className="rbac-readonly-note">
        <ShieldCheck size={17} />
        <div>
          <strong>Read-only RBAC view</strong>
          <span>Role creation and permission editing are intentionally not exposed in the Core UI yet.</span>
        </div>
      </div>

      {isLoading ? <div className="empty-state-panel">Loading roles and permissions.</div> : null}
      {!isLoading && !error && roles.length === 0 ? (
        <div className="empty-state-panel">No roles are available for this Core environment.</div>
      ) : null}

      <div className="roles-grid">
        {roles.map((role) => (
          <article className="role-card" key={role.slug}>
            <div className="role-card-header">
              <div>
                <span className="eyebrow">Role</span>
                <h3>{role.name}</h3>
              </div>
              <span className="state-pill">{role.slug}</span>
            </div>

            <div className="role-section">
              <div className="role-section-title">
                <KeyRound size={15} />
                <strong>Permissions</strong>
              </div>
              <div className="permission-list">
                {role.permissions.length === 0 ? (
                  <span className="empty-table-note">No permissions assigned.</span>
                ) : (
                  role.permissions.map((permission) => (
                    <code className="permission-chip" key={permission}>
                      {permission}
                    </code>
                  ))
                )}
              </div>
            </div>

            <div className="role-section">
              <div className="role-section-title">
                <Users size={15} />
                <strong>Users</strong>
              </div>
              <div className="role-user-list">
                {role.users.length === 0 ? (
                  <span className="empty-table-note">No users assigned.</span>
                ) : (
                  role.users.map((user) => (
                    <div className="role-user-row" key={user.id}>
                      <div>
                        <strong>{user.display_name}</strong>
                        <span>{user.email}</span>
                      </div>
                      <span className={`state-pill ${user.is_active ? "role-user-active" : "role-user-disabled"}`}>
                        {user.is_active ? "active" : "disabled"}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function sortRoles(roles: RoleItem[]) {
  return [...roles].sort((left, right) => {
    const leftIndex = CORE_ROLE_ORDER.indexOf(left.slug);
    const rightIndex = CORE_ROLE_ORDER.indexOf(right.slug);
    if (leftIndex !== -1 || rightIndex !== -1) {
      return (leftIndex === -1 ? Number.MAX_SAFE_INTEGER : leftIndex)
        - (rightIndex === -1 ? Number.MAX_SAFE_INTEGER : rightIndex);
    }
    return left.slug.localeCompare(right.slug);
  });
}

function normalizeRole(role: RoleItem): RoleItem {
  return {
    ...role,
    permissions: Array.isArray(role.permissions) ? role.permissions : [],
    users: Array.isArray(role.users) ? role.users : [],
  };
}

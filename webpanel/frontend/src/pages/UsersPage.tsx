import { KeyRound, Plus, ShieldCheck, UserCheck, UserX } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  createUser,
  listRoles,
  listUsers,
  resetUserPassword,
  updateUserActiveStatus,
  updateUserRoles,
  type ManagedUser,
  type RoleItem,
} from "../core/api/users";
import { apiErrorMessage } from "../core/api/client";
import { useAuth } from "../core/auth/AuthProvider";

const DEFAULT_ROLE = "viewer";

export function UsersPage() {
  const { token } = useAuth();
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [roles, setRoles] = useState<RoleItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [createDraft, setCreateDraft] = useState({
    email: "",
    displayName: "",
    password: "",
    role: DEFAULT_ROLE,
    isActive: true,
  });
  const [passwordDrafts, setPasswordDrafts] = useState<Record<number, string>>({});
  const roleOptions = useMemo(() => roles.map((role) => role.slug), [roles]);

  async function loadUsers() {
    if (!token) return;
    try {
      const [userResponse, roleResponse] = await Promise.all([listUsers(token), listRoles(token)]);
      setUsers(userResponse);
      setRoles(roleResponse);
      setError(null);
    } catch (loadError) {
      setError(apiErrorMessage(loadError, "Unable to load users."));
    }
  }

  useEffect(() => {
    void loadUsers();
  }, [token]);

  async function handleCreateUser() {
    if (!token) return;
    try {
      const created = await createUser(token, {
        email: createDraft.email,
        display_name: createDraft.displayName,
        password: createDraft.password,
        role_slugs: createDraft.role ? [createDraft.role] : [],
        is_active: createDraft.isActive,
      });
      setUsers((current) => [...current, created].sort((left, right) => left.email.localeCompare(right.email)));
      setCreateDraft({
        email: "",
        displayName: "",
        password: "",
        role: roleOptions.includes(DEFAULT_ROLE) ? DEFAULT_ROLE : (roleOptions[0] ?? ""),
        isActive: true,
      });
      setMessage(`Created ${created.email}.`);
      setError(null);
    } catch (createError) {
      setError(apiErrorMessage(createError, "Unable to create user."));
      setMessage(null);
    }
  }

  async function handleActiveChange(user: ManagedUser, isActive: boolean) {
    if (!token) return;
    try {
      const updated = await updateUserActiveStatus(token, user.id, isActive);
      updateUserInList(updated);
      setMessage(`${updated.email} is now ${updated.is_active ? "active" : "disabled"}.`);
      setError(null);
    } catch (activeError) {
      setError(apiErrorMessage(activeError, "Unable to update active status."));
      setMessage(null);
    }
  }

  async function handleRoleChange(user: ManagedUser, roleSlug: string) {
    if (!token) return;
    try {
      const updated = await updateUserRoles(token, user.id, roleSlug ? [roleSlug] : []);
      updateUserInList(updated);
      setMessage(`Updated roles for ${updated.email}.`);
      setError(null);
    } catch (roleError) {
      setError(apiErrorMessage(roleError, "Unable to update user roles."));
      setMessage(null);
    }
  }

  async function handlePasswordReset(user: ManagedUser) {
    if (!token) return;
    const password = passwordDrafts[user.id] ?? "";
    try {
      const updated = await resetUserPassword(token, user.id, password);
      updateUserInList(updated);
      setPasswordDrafts((current) => ({ ...current, [user.id]: "" }));
      setMessage(`Password reset for ${updated.email}.`);
      setError(null);
    } catch (passwordError) {
      setError(apiErrorMessage(passwordError, "Unable to reset password."));
      setMessage(null);
    }
  }

  function updateUserInList(updated: ManagedUser) {
    setUsers((current) => current.map((user) => (user.id === updated.id ? updated : user)));
  }

  return (
    <section className="data-page" aria-label="Users">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Core administration</span>
          <h2>Users</h2>
        </div>
        <span className="count-pill">{users.length} users</span>
      </div>

      {error ? <div className="login-error">{error}</div> : null}
      {message ? <div className="success-message">{message}</div> : null}

      <div className="user-create-panel">
        <label>
          Email
          <input
            onChange={(event) => setCreateDraft((current) => ({ ...current, email: event.target.value }))}
            value={createDraft.email}
          />
        </label>
        <label>
          Display name
          <input
            onChange={(event) =>
              setCreateDraft((current) => ({ ...current, displayName: event.target.value }))
            }
            value={createDraft.displayName}
          />
        </label>
        <label>
          Initial password
          <input
            onChange={(event) =>
              setCreateDraft((current) => ({ ...current, password: event.target.value }))
            }
            type="password"
            value={createDraft.password}
          />
        </label>
        <label>
          Role
          <select
            onChange={(event) => setCreateDraft((current) => ({ ...current, role: event.target.value }))}
            value={createDraft.role}
          >
            {roleOptions.map((role) => (
              <option key={role} value={role}>
                {role}
              </option>
            ))}
          </select>
        </label>
        <label className="checkbox-row">
          <input
            checked={createDraft.isActive}
            onChange={(event) =>
              setCreateDraft((current) => ({ ...current, isActive: event.target.checked }))
            }
            type="checkbox"
          />
          Active
        </label>
        <button className="primary-button" onClick={handleCreateUser} type="button">
          <Plus size={16} />
          Create
        </button>
      </div>

      <div className="data-table-wrap">
        <table className="data-table users-table">
          <thead>
            <tr>
              <th>User</th>
              <th>Status</th>
              <th>Role</th>
              <th>Password reset</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id}>
                <td>
                  <strong>{user.display_name}</strong>
                  <span>{user.email}</span>
                </td>
                <td>
                  <button
                    className={`icon-text-button ${user.is_active ? "state-active" : "state-disabled"}`}
                    onClick={() => handleActiveChange(user, !user.is_active)}
                    type="button"
                  >
                    {user.is_active ? <UserCheck size={15} /> : <UserX size={15} />}
                    {user.is_active ? "Active" : "Disabled"}
                  </button>
                </td>
                <td>
                  <label className="inline-control">
                    <ShieldCheck size={15} />
                    <select
                      onChange={(event) => handleRoleChange(user, event.target.value)}
                      value={user.roles[0] ?? ""}
                    >
                      <option value="">No role</option>
                      {roleOptions.map((role) => (
                        <option key={role} value={role}>
                          {role}
                        </option>
                      ))}
                    </select>
                  </label>
                </td>
                <td>
                  <div className="password-reset-row">
                    <input
                      onChange={(event) =>
                        setPasswordDrafts((current) => ({ ...current, [user.id]: event.target.value }))
                      }
                      placeholder="New password"
                      type="password"
                      value={passwordDrafts[user.id] ?? ""}
                    />
                    <button
                      className="icon-button"
                      onClick={() => handlePasswordReset(user)}
                      type="button"
                      aria-label={`Reset password for ${user.email}`}
                    >
                      <KeyRound size={16} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

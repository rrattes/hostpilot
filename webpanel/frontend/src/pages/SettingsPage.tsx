import { KeyRound, Save } from "lucide-react";
import { type FormEvent, useEffect, useMemo, useState } from "react";

import { changePassword } from "../core/api/auth";
import { listSettings, updateSetting, type Setting } from "../core/api/settings";
import { useAuth } from "../core/auth/AuthProvider";

interface SettingsPageProps {
  canEdit: boolean;
}

export function SettingsPage({ canEdit }: SettingsPageProps) {
  const { currentUser, token } = useAuth();
  const [settings, setSettings] = useState<Setting[]>([]);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [accountError, setAccountError] = useState<string | null>(null);
  const [accountMessage, setAccountMessage] = useState<string | null>(null);
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [passwordDraft, setPasswordDraft] = useState({
    currentPassword: "",
    newPassword: "",
    confirmPassword: "",
  });
  const passwordValidation = useMemo(
    () => validateNewPassword(passwordDraft.newPassword, passwordDraft.confirmPassword),
    [passwordDraft.confirmPassword, passwordDraft.newPassword],
  );

  useEffect(() => {
    if (!token) {
      return;
    }

    listSettings(token)
      .then((response) => {
        setSettings(response);
        setDrafts(Object.fromEntries(response.map((setting) => [setting.key, setting.value])));
      })
      .catch(() => setError("Unable to load settings."));
  }, [token]);

  async function handleSave(setting: Setting) {
    if (!token || !canEdit) {
      return;
    }

    try {
      const updated = await updateSetting(token, setting.key, drafts[setting.key] ?? "");
      setSettings((current) =>
        current.map((item) => (item.key === updated.key ? updated : item)),
      );
      setError(null);
    } catch {
      setError("Unable to update setting.");
    }
  }

  async function handleChangePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || isChangingPassword) {
      return;
    }

    const validationError = passwordValidation[0];
    if (!passwordDraft.currentPassword) {
      setAccountError("Current password is required.");
      setAccountMessage(null);
      return;
    }
    if (validationError) {
      setAccountError(validationError);
      setAccountMessage(null);
      return;
    }

    setIsChangingPassword(true);
    setAccountError(null);
    setAccountMessage(null);
    try {
      await changePassword(token, passwordDraft.currentPassword, passwordDraft.newPassword);
      setPasswordDraft({ currentPassword: "", newPassword: "", confirmPassword: "" });
      setAccountMessage("Password changed. Your current session remains active.");
    } catch {
      setAccountError("Unable to change password. Check your current password and password policy.");
    } finally {
      setIsChangingPassword(false);
    }
  }

  return (
    <section className="data-page" aria-label="Settings">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Core configuration</span>
          <h2>Settings</h2>
        </div>
      </div>

      {error ? <div className="login-error">{error}</div> : null}

      <article className="account-panel" aria-label="Account security">
        <div>
          <span className="eyebrow">Account security</span>
          <h3>Change password</h3>
          <p>
            Signed in as <strong>{currentUser?.email}</strong>. Password changes are audit recorded.
          </p>
        </div>

        <form className="account-password-form" onSubmit={handleChangePassword}>
          {accountError ? <div className="login-error">{accountError}</div> : null}
          {accountMessage ? <div className="success-message">{accountMessage}</div> : null}
          <div className="account-password-grid">
            <label>
              Current password
              <input
                autoComplete="current-password"
                onChange={(event) =>
                  setPasswordDraft((current) => ({ ...current, currentPassword: event.target.value }))
                }
                type="password"
                value={passwordDraft.currentPassword}
              />
            </label>
            <label>
              New password
              <input
                autoComplete="new-password"
                onChange={(event) =>
                  setPasswordDraft((current) => ({ ...current, newPassword: event.target.value }))
                }
                type="password"
                value={passwordDraft.newPassword}
              />
            </label>
            <label>
              Confirm new password
              <input
                autoComplete="new-password"
                onChange={(event) =>
                  setPasswordDraft((current) => ({ ...current, confirmPassword: event.target.value }))
                }
                type="password"
                value={passwordDraft.confirmPassword}
              />
            </label>
          </div>
          <div className="password-policy-list">
            {passwordValidation.map((item) => (
              <span key={item}>{item}</span>
            ))}
          </div>
          <button className="primary-button compact" disabled={isChangingPassword} type="submit">
            <KeyRound size={16} />
            {isChangingPassword ? "Changing" : "Change password"}
          </button>
        </form>
      </article>

      <div className="settings-list">
        {settings.map((setting) => (
          <article className="setting-row" key={setting.key}>
            <div>
              <h3>{setting.key}</h3>
              <p>{setting.is_sensitive ? "Sensitive value hidden" : "Core setting"}</p>
            </div>
            <div className="setting-editor">
              <input
                disabled={!canEdit || setting.is_sensitive}
                onChange={(event) =>
                  setDrafts((current) => ({ ...current, [setting.key]: event.target.value }))
                }
                value={drafts[setting.key] ?? ""}
              />
              {canEdit ? (
                <button className="icon-button" onClick={() => handleSave(setting)} type="button" aria-label="Save setting">
                  <Save size={16} />
                </button>
              ) : null}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function validateNewPassword(password: string, confirmation: string) {
  const issues: string[] = [];
  if (password.length < 12) issues.push("Use at least 12 characters.");
  if (!/[a-z]/.test(password)) issues.push("Add a lowercase letter.");
  if (!/[A-Z]/.test(password)) issues.push("Add an uppercase letter.");
  if (!/\d/.test(password)) issues.push("Add a number.");
  if (!/[^\w\s]/.test(password)) issues.push("Add a symbol.");
  if (!confirmation) issues.push("Confirm the new password.");
  if (confirmation && password !== confirmation) issues.push("New password and confirmation must match.");
  return issues;
}

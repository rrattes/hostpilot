import { Save } from "lucide-react";
import { useEffect, useState } from "react";

import { listSettings, updateSetting, type Setting } from "../core/api/settings";
import { useAuth } from "../core/auth/AuthProvider";

interface SettingsPageProps {
  canEdit: boolean;
}

export function SettingsPage({ canEdit }: SettingsPageProps) {
  const { token } = useAuth();
  const [settings, setSettings] = useState<Setting[]>([]);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

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

  return (
    <section className="data-page" aria-label="Settings">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Core configuration</span>
          <h2>Settings</h2>
        </div>
      </div>

      {error ? <div className="login-error">{error}</div> : null}

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

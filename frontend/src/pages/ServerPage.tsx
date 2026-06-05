import { Save } from "lucide-react";
import { useEffect, useState } from "react";

import { getLocalServer, updateLocalServer, type LocalServer } from "../core/api/server";
import { useAuth } from "../core/auth/AuthProvider";

interface ServerPageProps {
  canEdit: boolean;
}

export function ServerPage({ canEdit }: ServerPageProps) {
  const { token } = useAuth();
  const [server, setServer] = useState<LocalServer | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      return;
    }

    getLocalServer(token)
      .then((response) => {
        setServer(response);
        setName(response.name);
        setDescription(response.description);
      })
      .catch(() => setError("Unable to load local server."));
  }, [token]);

  async function handleSave() {
    if (!token || !canEdit) {
      return;
    }

    try {
      const updated = await updateLocalServer(token, name, description);
      setServer(updated);
      setError(null);
    } catch {
      setError("Unable to update server display data.");
    }
  }

  return (
    <section className="data-page" aria-label="Server">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Local record</span>
          <h2>Server</h2>
        </div>
        {canEdit ? (
          <button className="primary-button compact" onClick={handleSave} type="button">
            <Save size={16} />
            Save
          </button>
        ) : null}
      </div>

      {error ? <div className="login-error">{error}</div> : null}

      <div className="server-panel">
        <label>
          <span>Name</span>
          <input disabled={!canEdit} onChange={(event) => setName(event.target.value)} value={name} />
        </label>
        <label>
          <span>Description</span>
          <textarea
            disabled={!canEdit}
            onChange={(event) => setDescription(event.target.value)}
            value={description}
          />
        </label>
        <div className="server-facts">
          <span>Hostname: {server?.hostname ?? "loading"}</span>
          <span>OS: {server?.os_name ?? "loading"}</span>
        </div>
      </div>
    </section>
  );
}

import { Archive, CheckCircle2, DatabaseBackup, HardDrive, Plus, ShieldAlert } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  createCoreBackup,
  listCoreBackups,
  type CoreBackup,
} from "../core/api/backups";
import { useAuth } from "../core/auth/AuthProvider";

interface BackupsPageProps {
  canCreate: boolean;
}

export function BackupsPage({ canCreate }: BackupsPageProps) {
  const { token } = useAuth();
  const [backups, setBackups] = useState<CoreBackup[]>([]);
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const totalSize = useMemo(
    () => backups.reduce((total, backup) => total + backup.size_bytes, 0),
    [backups],
  );

  async function loadBackups() {
    if (!token) return false;
    try {
      setBackups(await listCoreBackups(token));
      setError(null);
      return true;
    } catch {
      setError("Unable to load Core backup metadata.");
      return false;
    }
  }

  useEffect(() => {
    void loadBackups();
  }, [token]);

  async function handleCreateBackup() {
    if (!token || !canCreate || isCreating) return;
    setIsCreating(true);
    setMessage(null);
    setError(null);
    try {
      const backup = await createCoreBackup(token);
      const refreshed = await loadBackups();
      setMessage(
        refreshed
          ? `Core backup ${safeBackupName(backup.file_path)} created and backup list refreshed.`
          : `Core backup ${safeBackupName(backup.file_path)} created, but metadata refresh failed.`,
      );
    } catch {
      setError("Core backup failed. Review the audit log and backend logs.");
    } finally {
      setIsCreating(false);
    }
  }

  return (
    <section className="data-page" aria-label="Core backups">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Core safeguards</span>
          <h2>Backups</h2>
        </div>
        <div className="page-actions">
          <span className="count-pill">
            <Archive size={14} />
            {backups.length} backups
          </span>
          <span className="count-pill">
            <HardDrive size={14} />
            {formatBytes(totalSize)}
          </span>
          {canCreate ? (
            <button
              className="primary-button compact"
              disabled={isCreating}
              onClick={handleCreateBackup}
              type="button"
            >
              <Plus size={16} />
              {isCreating ? "Creating" : "Create Core Backup"}
            </button>
          ) : null}
        </div>
      </div>

      {error ? <div className="login-error">{error}</div> : null}
      {message ? <div className="success-message">{message}</div> : null}

      <div className="backup-scope-note">
        <DatabaseBackup size={17} />
        <div>
          <strong>Core-only backup</strong>
          <span>Captures the Core SQLite database and existing Core config/state files. Restore, scheduling, cloud, website, Nginx, and SSL backups are intentionally excluded.</span>
        </div>
      </div>

      <div className="data-table-wrap">
        <table className="data-table backups-table">
          <thead>
            <tr>
              <th>Created</th>
              <th>Actor</th>
              <th>Status</th>
              <th>Size</th>
              <th>Archive</th>
            </tr>
          </thead>
          <tbody>
            {backups.length === 0 ? (
              <tr>
                <td colSpan={5}>
                  <span className="empty-table-note">No Core backup metadata has been recorded yet.</span>
                </td>
              </tr>
            ) : (
              backups.map((backup) => (
                <tr key={backup.id}>
                  <td>
                    <strong>{formatDate(backup.created_at)}</strong>
                    <span>{backup.id}</span>
                  </td>
                  <td>{backup.created_by === null ? "system" : `user #${backup.created_by}`}</td>
                  <td>
                    <span className={`state-pill backup-status ${backup.status}`}>
                      {backup.status === "completed" ? <CheckCircle2 size={14} /> : <ShieldAlert size={14} />}
                      {backup.status}
                    </span>
                  </td>
                  <td>{formatBytes(backup.size_bytes)}</td>
                  <td>
                    <code className="path-code">{safeBackupName(backup.file_path)}</code>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatBytes(value: number) {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

function safeBackupName(filePath: string) {
  return filePath.split(/[\\/]/).pop() ?? filePath;
}

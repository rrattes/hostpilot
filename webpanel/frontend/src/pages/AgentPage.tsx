import { Play } from "lucide-react";
import { useEffect, useState } from "react";

import {
  executeMockAgentAction,
  getAgentStatus,
  listRecentAgentJobs,
  type AgentJob,
  type AgentStatus,
} from "../core/api/agent";
import { useAuth } from "../core/auth/AuthProvider";

interface AgentPageProps {
  canExecuteMock: boolean;
}

export function AgentPage({ canExecuteMock }: AgentPageProps) {
  const { token } = useAuth();
  const [status, setStatus] = useState<AgentStatus | null>(null);
  const [jobs, setJobs] = useState<AgentJob[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function loadAgent() {
    if (!token) {
      return;
    }

    try {
      const [agentStatus, recentJobs] = await Promise.all([
        getAgentStatus(token),
        listRecentAgentJobs(token),
      ]);
      setStatus(agentStatus);
      setJobs(recentJobs);
      setError(null);
    } catch {
      setError("Unable to load agent gateway.");
    }
  }

  useEffect(() => {
    void loadAgent();
  }, [token]);

  async function handleExecute(action: string) {
    if (!token || !canExecuteMock) {
      return;
    }

    try {
      await executeMockAgentAction(token, action);
      await loadAgent();
    } catch {
      setError("Unable to execute mock agent action.");
    }
  }

  return (
    <section className="data-page" aria-label="Agent">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Mock gateway</span>
          <h2>Agent</h2>
        </div>
        <span className="count-pill">{status?.mode ?? "mock"}</span>
      </div>

      {error ? <div className="login-error">{error}</div> : null}

      <div className="summary-grid">
        <div className="summary-panel">
          <span className="metric-label">Status</span>
          <strong>{status?.status ?? "Unknown"}</strong>
          <p>Agent gateway is currently backed by safe mock actions only.</p>
        </div>
        <div className="summary-panel">
          <span className="metric-label">Allowed actions</span>
          <strong>{status?.allowed_actions.length ?? 0}</strong>
          <p>No shell, package manager, service, or infrastructure actions are available.</p>
        </div>
      </div>

      <div className="module-grid">
        {status?.allowed_actions.map((action) => (
          <article className="module-card disabled" key={action}>
            <div className="module-card-header">
              <h3>{action}</h3>
              <span className="state-pill">Mock</span>
            </div>
            <p>Allowlisted mock action exposed by the development agent contract.</p>
            {canExecuteMock ? (
              <button className="primary-button compact" onClick={() => handleExecute(action)} type="button">
                <Play size={15} />
                Execute
              </button>
            ) : null}
          </article>
        ))}
      </div>

      <div className="data-table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Created</th>
              <th>Action</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.id}>
                <td>{formatDate(job.created_at)}</td>
                <td>{job.action}</td>
                <td>{job.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "short",
    timeStyle: "medium",
  }).format(new Date(value));
}

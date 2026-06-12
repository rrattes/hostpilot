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
          <span className="eyebrow">Agent gateway</span>
          <h2>Agent</h2>
        </div>
        <span className="count-pill">{status?.mode ?? "checking"}</span>
      </div>

      {error ? <div className="login-error">{error}</div> : null}

      <div className="summary-grid">
        <div className="summary-panel">
          <span className="metric-label">Status</span>
          <strong>{status ? agentStatusLabel(status.status) : "Unknown"}</strong>
          <p>{status?.message ?? "Checking whether the local Agent is reachable."}</p>
        </div>
        <div className="summary-panel">
          <span className="metric-label">Web controlled actions</span>
          <strong>{status?.web_actions_use_real_agent ? "Real Agent" : "Not real Agent"}</strong>
          <p>{status?.using_fallback ? "Windows/dev fallback is active and clearly labeled." : "No arbitrary commands are exposed."}</p>
        </div>
      </div>

      <div className="module-grid">
        {status?.allowed_actions.map((action) => (
          <article className="module-card disabled" key={action}>
            <div className="module-card-header">
              <h3>{action}</h3>
              <span className="state-pill">{status.using_real_agent ? "Agent" : "Fallback"}</span>
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

function agentStatusLabel(status: AgentStatus["status"]) {
  if (status === "connected") return "Connected";
  if (status === "fallback") return "Fallback (dev)";
  return "Unavailable";
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "short",
    timeStyle: "medium",
  }).format(new Date(value));
}

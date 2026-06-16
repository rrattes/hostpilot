import { Plus } from "lucide-react";
import { useEffect, useState } from "react";

import { createMockJob, listJobs, type Job } from "../core/api/jobs";
import { useAuth } from "../core/auth/AuthProvider";

interface JobsPageProps {
  devActionsEnabled: boolean;
}

export function JobsPage({ devActionsEnabled }: JobsPageProps) {
  const { token } = useAuth();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  async function loadJobs() {
    if (!token) {
      return;
    }

    try {
      const response = await listJobs(token);
      setJobs(response.items);
      setTotal(response.total);
      setError(null);
    } catch {
      setError("Unable to load jobs.");
    }
  }

  useEffect(() => {
    void loadJobs();
  }, [token]);

  async function handleCreateMockJob() {
    if (!token) {
      return;
    }

    setIsCreating(true);
    try {
      await createMockJob(token);
      await loadJobs();
    } catch {
      setError("Unable to create mock job.");
    } finally {
      setIsCreating(false);
    }
  }

  return (
    <section className="data-page" aria-label="Jobs">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Core queue</span>
          <h2>Jobs</h2>
        </div>
        <div className="page-actions">
          <span className="count-pill">{total} jobs</span>
          {devActionsEnabled ? (
            <button className="primary-button compact" disabled={isCreating} onClick={handleCreateMockJob} type="button">
              <Plus size={16} />
              Development only: mock job
            </button>
          ) : null}
        </div>
      </div>

      {error ? <div className="login-error">{error}</div> : null}

      <div className="data-table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Created</th>
              <th>Module</th>
              <th>Action</th>
              <th>Status</th>
              <th>Type</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.id}>
                <td>{formatDate(job.created_at)}</td>
                <td>{job.module}</td>
                <td>{job.action}</td>
                <td>{job.status}</td>
                <td>{job.type}</td>
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

import { useEffect, useState } from "react";

import { listAuditEvents, type AuditEvent } from "../core/api/audit";
import { useAuth } from "../core/auth/AuthProvider";

export function AuditLogPage() {
  const { token } = useAuth();
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      return;
    }

    listAuditEvents(token)
      .then((response) => {
        setEvents(response.items);
        setTotal(response.total);
      })
      .catch(() => setError("Unable to load audit events."));
  }, [token]);

  return (
    <section className="data-page" aria-label="Audit Log">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Core records</span>
          <h2>Audit Log</h2>
        </div>
        <span className="count-pill">{total} events</span>
      </div>

      {error ? <div className="login-error">{error}</div> : null}

      <div className="data-table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Action</th>
              <th>Outcome</th>
              <th>Actor</th>
              <th>Target</th>
            </tr>
          </thead>
          <tbody>
            {events.map((event) => (
              <tr key={event.id}>
                <td>{formatDate(event.created_at)}</td>
                <td>{event.action}</td>
                <td>{event.outcome}</td>
                <td>{event.actor_user_id ?? "system"}</td>
                <td>
                  {event.target_type}
                  {event.target_id ? `:${event.target_id}` : ""}
                </td>
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

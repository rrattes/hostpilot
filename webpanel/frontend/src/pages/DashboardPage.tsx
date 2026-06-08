import { Lock, Settings, ShieldCheck } from "lucide-react";

import {
  moduleCardState,
  moduleDescription,
  moduleStatusLabel,
  type ModuleDefinition,
  type ModuleState,
} from "../core/modules/moduleCatalog";
import type { AgentStatus } from "../core/api/agent";
import type { CoreHealthStatus } from "../core/api/status";

interface DashboardPageProps {
  canManageModules: boolean;
  agentStatus: AgentStatus | null;
  healthStatus: CoreHealthStatus | null;
  modules: ModuleDefinition[];
  onModuleStateChange: (slug: string, state: ModuleState) => void;
}

export function DashboardPage({
  canManageModules,
  agentStatus,
  healthStatus,
  modules,
  onModuleStateChange,
}: DashboardPageProps) {
  const activeModules =
    healthStatus?.enabled_modules_count ?? modules.filter((module) => module.state === "enabled").length;
  const lockedModules =
    healthStatus?.locked_modules_count ?? modules.filter((module) => module.state === "locked").length;

  return (
    <div className="dashboard">
      <section className="summary-grid" aria-label="Core summary">
        <div className="summary-panel summary-panel-primary">
          <span className="metric-label">Core status</span>
          <strong>{healthStatus?.core_status === "ok" ? "Active" : "Loading"}</strong>
          <p>
            DB {healthStatus?.database_status ?? "checking"} · Agent{" "}
            {healthStatus?.agent_mock_status ?? "checking"}
          </p>
        </div>
        <div className="summary-panel">
          <span className="metric-label">Enabled modules</span>
          <strong>{activeModules}</strong>
          <p>Only the Core is functional in this scaffold.</p>
        </div>
        <div className="summary-panel">
          <span className="metric-label">Locked modules</span>
          <strong>{lockedModules}</strong>
          <p>Future vertical capabilities are visible but unavailable.</p>
        </div>
        <div className="summary-panel summary-panel-wide">
          <span className="metric-label">Recent jobs</span>
          <strong>{healthStatus?.recent_jobs_count ?? 0}</strong>
          <p>Mock/dev and Core job records in the last 24 hours.</p>
        </div>
        <div className="summary-panel summary-panel-wide">
          <span className="metric-label">Recent audit</span>
          <strong>{healthStatus?.recent_audit_events_count ?? 0}</strong>
          <p>Security and Core activity records in the last 24 hours.</p>
        </div>
        <div className="summary-panel summary-panel-wide">
          <span className="metric-label">Local server</span>
          <strong>{healthStatus?.local_server?.name ?? "Not loaded"}</strong>
          <p>{healthStatus?.local_server?.hostname ?? "Waiting for Core status."}</p>
        </div>
        <div className="summary-panel summary-panel-wide">
          <span className="metric-label">Agent</span>
          <strong>{agentStatus?.status ?? "Unknown"}</strong>
          <p>
            {agentStatus
              ? `${agentStatus.mode} · ${agentStatus.allowed_actions.length} allowed mock actions`
              : "Waiting for mock agent gateway."}
          </p>
        </div>
      </section>

      <section className="module-section" aria-label="Module catalog">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Registry preview</span>
            <h2>Modules</h2>
          </div>
        </div>

        <div className="module-grid">
          {modules.map((module) => (
            <article className={`module-card ${moduleCardState(module)}`} key={module.slug}>
              <div className="module-card-header">
                <h3>{module.name}</h3>
                <span className="state-pill">
                  {module.state === "enabled" ? <ShieldCheck size={14} /> : <Lock size={14} />}
                  {moduleStatusLabel(module)}
                </span>
              </div>
              <p>{moduleDescription(module.slug)}</p>
              {canManageModules && module.slug !== "core" ? (
                <label className="module-control">
                  <Settings size={14} />
                  <select
                    onChange={(event) =>
                      onModuleStateChange(module.slug, event.target.value as ModuleState)
                    }
                    value={module.state}
                  >
                    <option value="available">Available</option>
                    <option value="installed">Installed</option>
                    <option value="enabled">Enabled</option>
                    <option value="locked">Locked</option>
                  </select>
                </label>
              ) : null}
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

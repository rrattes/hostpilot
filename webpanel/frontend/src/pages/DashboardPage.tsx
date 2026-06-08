import {
  Activity,
  Clock3,
  Database,
  History,
  Layers3,
  Lock,
  RadioTower,
  Server,
  Settings,
  ShieldCheck,
} from "lucide-react";
import type { ReactNode } from "react";

import type { AgentStatus } from "../core/api/agent";
import type { CoreHealthStatus } from "../core/api/status";
import {
  moduleCardState,
  moduleDescription,
  moduleStatusLabel,
  type ModuleDefinition,
  type ModuleState,
} from "../core/modules/moduleCatalog";

interface DashboardPageProps {
  canManageModules: boolean;
  agentStatus: AgentStatus | null;
  healthStatus: CoreHealthStatus | null;
  modules: ModuleDefinition[];
  onModuleStateChange: (slug: string, state: ModuleState) => void;
}

interface MetricCardProps {
  description: string;
  icon: ReactNode;
  label: string;
  tone?: "default" | "primary";
  value: number | string;
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
      <section className="dashboard-section" aria-label="Core runtime">
        <div className="dashboard-section-heading">
          <div>
            <span className="eyebrow">Runtime</span>
            <h2>Core status</h2>
          </div>
          <span className="section-chip">
            <Activity size={14} />
            Live checks
          </span>
        </div>

        <div className="summary-grid summary-grid-runtime">
          <MetricCard
            description={`DB ${healthStatus?.database_status ?? "checking"} / Agent ${
              healthStatus?.agent_mock_status ?? "checking"
            }`}
            icon={<ShieldCheck size={17} />}
            label="Core"
            tone="primary"
            value={healthStatus?.core_status === "ok" ? "Active" : "Loading"}
          />
          <MetricCard
            description="Only the Core is functional in this scaffold."
            icon={<Layers3 size={17} />}
            label="Enabled modules"
            value={activeModules}
          />
          <MetricCard
            description="Future vertical capabilities are visible but unavailable."
            icon={<Lock size={17} />}
            label="Locked modules"
            value={lockedModules}
          />
        </div>
      </section>

      <section className="dashboard-section" aria-label="Core activity">
        <div className="dashboard-section-heading compact">
          <div>
            <span className="eyebrow">Activity</span>
            <h2>Last 24 hours</h2>
          </div>
        </div>

        <div className="summary-grid summary-grid-activity">
          <MetricCard
            description="Mock/dev and Core job records in the last 24 hours."
            icon={<Clock3 size={17} />}
            label="Recent jobs"
            value={healthStatus?.recent_jobs_count ?? 0}
          />
          <MetricCard
            description="Security and Core activity records in the last 24 hours."
            icon={<History size={17} />}
            label="Recent audit"
            value={healthStatus?.recent_audit_events_count ?? 0}
          />
          <MetricCard
            description={healthStatus?.local_server?.hostname ?? "Waiting for Core status."}
            icon={<Server size={17} />}
            label="Local server"
            value={healthStatus?.local_server?.name ?? "Not loaded"}
          />
          <MetricCard
            description={
              agentStatus
                ? `${agentStatus.mode} / ${agentStatus.allowed_actions.length} allowed mock actions`
                : "Waiting for mock agent gateway."
            }
            icon={<RadioTower size={17} />}
            label="Agent"
            value={agentStatus?.status ?? "Unknown"}
          />
        </div>
      </section>

      <section className="module-section" aria-label="Module catalog">
        <div className="section-heading dashboard-section-heading">
          <div>
            <span className="eyebrow">Registry preview</span>
            <h2>Modules</h2>
          </div>
          <span className="section-chip">
            <Database size={14} />
            Registry
          </span>
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

function MetricCard({ description, icon, label, tone = "default", value }: MetricCardProps) {
  return (
    <div className={`summary-panel ${tone === "primary" ? "summary-panel-primary" : ""}`}>
      <div className="summary-panel-header">
        <span className="summary-icon">{icon}</span>
        <span className="metric-label">{label}</span>
      </div>
      <strong>{value}</strong>
      <p>{description}</p>
    </div>
  );
}

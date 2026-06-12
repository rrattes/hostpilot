import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Database,
  GitBranch,
  Layers3,
  Lock,
  RadioTower,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import type { ReactNode } from "react";

import type { AgentStatus } from "../core/api/agent";
import type { CoreHealthStatus } from "../core/api/status";
import {
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

interface OverviewMetricProps {
  description: string;
  icon: ReactNode;
  label: string;
  tone: "cyan" | "blue" | "purple" | "pink";
  value: number | string;
}

const activityPoints = [18, 34, 27, 52, 44, 69, 58, 82, 76, 91, 84, 97];

export function DashboardPage({
  agentStatus,
  healthStatus,
  modules,
}: DashboardPageProps) {
  const enabledModules =
    healthStatus?.enabled_modules_count ?? modules.filter((module) => module.state === "enabled").length;
  const lockedModules =
    healthStatus?.locked_modules_count ?? modules.filter((module) => module.state === "locked").length;
  const issueCount = Number(healthStatus?.database_status !== "ok") + Number(agentStatus?.status === "error");
  const recentJobs = healthStatus?.recent_jobs_count ?? 0;
  const recentAudit = healthStatus?.recent_audit_events_count ?? 0;
  const jobDonutStyle = {
    "--done": `${Math.max(22, Math.min(72, 36 + recentJobs * 4))}%`,
    "--queued": `${Math.max(12, Math.min(28, 18 + recentAudit))}%`,
  } as React.CSSProperties;

  return (
    <div className="dashboard dashboard-overview">
      <section className="overview-hero" aria-label="HostPilot overview">
        <div>
          <span className="eyebrow">Overview</span>
          <h2>Environment command center</h2>
          <p>
            Core health, activity, jobs, and module posture in one focused view.
          </p>
        </div>
        <div className="overview-hero-status">
          <span>
            <ShieldCheck size={16} />
            Core {healthStatus?.core_status ?? "checking"}
          </span>
          <span>
            <RadioTower size={16} />
            Agent {agentStatus?.status ?? "checking"}
          </span>
        </div>
      </section>

      <section className="overview-metrics" aria-label="Summary metrics">
        <OverviewMetric
          description={`Database ${healthStatus?.database_status ?? "checking"} / Agent ${
            healthStatus?.agent_mock_status ?? "checking"
          }`}
          icon={<ShieldCheck size={20} />}
          label="Core Status"
          tone="cyan"
          value={healthStatus?.core_status === "ok" ? "Operational" : "Checking"}
        />
        <OverviewMetric
          description={`${lockedModules} locked or unavailable capabilities`}
          icon={<Layers3 size={20} />}
          label="Modules Enabled"
          tone="blue"
          value={enabledModules}
        />
        <OverviewMetric
          description="Database and agent checks requiring attention"
          icon={<AlertTriangle size={20} />}
          label="Alerts / Issues"
          tone="pink"
          value={issueCount}
        />
        <OverviewMetric
          description="Job records created in the last 24 hours"
          icon={<Clock3 size={20} />}
          label="Recent Jobs"
          tone="purple"
          value={recentJobs}
        />
      </section>

      <section className="overview-main-grid" aria-label="Dashboard details">
        <article className="overview-panel system-activity-panel">
          <PanelHeader
            eyebrow="Telemetry"
            icon={<Activity size={16} />}
            title="System Activity"
          />
          <div className="activity-chart" aria-label="System activity chart">
            <svg viewBox="0 0 480 180" role="img" aria-label="Activity trend">
              <defs>
                <linearGradient id="activityFill" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor="#22d3ee" stopOpacity="0.42" />
                  <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0.02" />
                </linearGradient>
                <linearGradient id="activityLine" x1="0" x2="1" y1="0" y2="0">
                  <stop offset="0%" stopColor="#22d3ee" />
                  <stop offset="55%" stopColor="#3b82f6" />
                  <stop offset="100%" stopColor="#ec4899" />
                </linearGradient>
              </defs>
              <path className="activity-grid-line" d="M0 42H480M0 90H480M0 138H480" />
              <path className="activity-fill" d={activityAreaPath(activityPoints)} />
              <path className="activity-line" d={activityLinePath(activityPoints)} />
            </svg>
          </div>
          <div className="activity-stats">
            <span>
              <strong>{recentAudit}</strong>
              audit events
            </span>
            <span>
              <strong>{healthStatus?.runtime ?? "FastAPI"}</strong>
              runtime
            </span>
            <span>
              <strong>{healthStatus?.database ?? "SQLite"}</strong>
              database
            </span>
          </div>
        </article>

        <article className="overview-panel jobs-panel">
          <PanelHeader eyebrow="Operations" icon={<GitBranch size={16} />} title="Jobs by Status" />
          <div className="jobs-donut-wrap">
            <div className="jobs-donut" style={jobDonutStyle}>
              <span>{recentJobs}</span>
            </div>
            <div className="jobs-legend">
              <span><i className="legend-dot done" />Completed</span>
              <span><i className="legend-dot queued" />Queued</span>
              <span><i className="legend-dot review" />Review</span>
            </div>
          </div>
        </article>

        <article className="overview-panel activity-list-panel">
          <PanelHeader eyebrow="Timeline" icon={<Sparkles size={16} />} title="Recent Activity" />
          <div className="activity-timeline">
            <TimelineItem
              detail={`${recentAudit} audit events in the last 24 hours`}
              label="Audit stream active"
              tone="cyan"
            />
            <TimelineItem
              detail={`${recentJobs} recent jobs recorded`}
              label="Job queue observed"
              tone="purple"
            />
            <TimelineItem
              detail={healthStatus?.local_server?.hostname ?? "Local server pending status"}
              label="Local server check"
              tone="blue"
            />
          </div>
        </article>

        <article className="overview-panel modules-snapshot-panel">
          <PanelHeader eyebrow="Registry" icon={<Database size={16} />} title="Modules Snapshot" />
          <div className="module-snapshot-grid">
            {snapshotModules(modules).map((module) => (
              <div className={`module-snapshot-item ${module.state}`} key={module.slug}>
                <strong>{module.name}</strong>
                <span>{moduleDescription(module.slug)}</span>
                <em>
                  {module.state === "enabled" ? <CheckCircle2 size={13} /> : <Lock size={13} />}
                  {moduleStatusLabel(module)}
                </em>
              </div>
            ))}
          </div>
        </article>
      </section>
    </div>
  );
}

function OverviewMetric({ description, icon, label, tone, value }: OverviewMetricProps) {
  return (
    <article className={`overview-metric-card ${tone}`}>
      <div className="overview-metric-top">
        <span className="overview-metric-icon">{icon}</span>
        <span>{label}</span>
      </div>
      <strong>{value}</strong>
      <p>{description}</p>
    </article>
  );
}

function PanelHeader({ eyebrow, icon, title }: { eyebrow: string; icon: ReactNode; title: string }) {
  return (
    <div className="overview-panel-header">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h3>{title}</h3>
      </div>
      <span className="overview-panel-icon">{icon}</span>
    </div>
  );
}

function TimelineItem({
  detail,
  label,
  tone,
}: {
  detail: string;
  label: string;
  tone: "cyan" | "blue" | "purple";
}) {
  return (
    <div className={`timeline-item ${tone}`}>
      <span />
      <div>
        <strong>{label}</strong>
        <p>{detail}</p>
      </div>
    </div>
  );
}

function snapshotModules(modules: ModuleDefinition[]) {
  const wanted = ["core", "backups", "logs", "nginx", "ssl", "docker", "kvm", "remote-access"];
  const bySlug = new Map(modules.map((module) => [module.slug, module]));
  return wanted.map((slug) => {
    const existing = bySlug.get(slug);
    if (existing) return existing;
    return {
      slug,
      name: labelFromSlug(slug),
      version: "0.0.0",
      state: "locked" as ModuleState,
      enabled: false,
      locked: true,
      installed: false,
    };
  });
}

function labelFromSlug(slug: string) {
  return slug
    .split("-")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function activityLinePath(points: number[]) {
  return points
    .map((point, index) => {
      const x = (index / (points.length - 1)) * 480;
      const y = 170 - point * 1.45;
      return `${index === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(" ");
}

function activityAreaPath(points: number[]) {
  return `${activityLinePath(points)} L480 180 L0 180 Z`;
}

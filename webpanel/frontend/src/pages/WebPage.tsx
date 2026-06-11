import {
  Braces,
  FileText,
  Globe2,
  Lock,
  ScrollText,
  ServerCog,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { getWebStatus, type WebSectionStatus, type WebStatus } from "../core/api/web";
import { useAuth } from "../core/auth/AuthProvider";

const sectionIcons = {
  sites: Globe2,
  nginx: ServerCog,
  ssl: ShieldCheck,
  logs: ScrollText,
  "php-runtime": Braces,
};

interface WebPageProps {
  moduleState: string;
}

export function WebPage({ moduleState }: WebPageProps) {
  const { token } = useAuth();
  const [status, setStatus] = useState<WebStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const sections = useMemo(() => status?.sections ?? fallbackSections(), [status]);

  useEffect(() => {
    if (!token) return;

    getWebStatus(token)
      .then((response) => {
        setStatus(response);
        setError(null);
      })
      .catch(() => setError("Unable to load Web module scaffold status."));
  }, [token]);

  return (
    <section className="data-page web-page" aria-label="Web module">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Module scaffold</span>
          <h2>Web</h2>
        </div>
        <div className="page-actions">
          <span className="count-pill">
            <Lock size={14} />
            Actions unavailable
          </span>
          <span className="count-pill">
            <ShieldAlert size={14} />
            {status?.module_state ?? moduleState}
          </span>
        </div>
      </div>

      {error ? <div className="login-error">{error}</div> : null}

      <div className="web-scope-note">
        <FileText size={17} />
        <div>
          <strong>Read-only scaffold</strong>
          <span>
            This page exposes module shape and status only. It does not create sites, edit Nginx,
            request SSL certificates, manage PHP, read logs, or execute Agent actions.
          </span>
        </div>
      </div>

      <div className="web-status-grid">
        <div className="summary-panel summary-panel-primary">
          <div className="summary-panel-header">
            <span className="summary-icon">
              <Globe2 size={17} />
            </span>
            <span className="metric-label">Module state</span>
          </div>
          <strong>{status?.module_state ?? moduleState}</strong>
          <p>Registered as a visible scaffold while operational Web features remain disabled.</p>
        </div>
        <div className="summary-panel">
          <div className="summary-panel-header">
            <span className="summary-icon">
              <Lock size={17} />
            </span>
            <span className="metric-label">Operational</span>
          </div>
          <strong>{status?.operational ? "Active" : "No"}</strong>
          <p>No system, Nginx, SSL, PHP, site, deploy, or Agent workflow is enabled.</p>
        </div>
      </div>

      <div className="web-section-grid">
        {sections.map((section) => (
          <WebSectionCard key={section.slug} section={section} />
        ))}
      </div>
    </section>
  );
}

function WebSectionCard({ section }: { section: WebSectionStatus }) {
  const Icon = sectionIcons[section.slug as keyof typeof sectionIcons] ?? FileText;

  return (
    <article className="web-section-card">
      <div className="web-section-card-header">
        <span className="summary-icon">
          <Icon size={17} />
        </span>
        <span className="state-pill">
          <Lock size={14} />
          {section.status === "coming_soon" ? "Coming soon" : "Unavailable"}
        </span>
      </div>
      <h3>{section.name}</h3>
      <p>{section.description}</p>
      <button className="icon-text-button state-disabled" disabled type="button">
        <Lock size={15} />
        {section.action_label}
      </button>
    </article>
  );
}

function fallbackSections(): WebSectionStatus[] {
  return [
    {
      slug: "sites",
      name: "Sites",
      status: "coming_soon",
      description: "Website records and lifecycle workflows are not active in this scaffold.",
      action_label: "Site creation coming soon",
      action_available: false,
    },
    {
      slug: "nginx",
      name: "Nginx",
      status: "unavailable",
      description: "Nginx configuration checks and file edits are intentionally disabled.",
      action_label: "Nginx actions unavailable",
      action_available: false,
    },
    {
      slug: "ssl",
      name: "SSL",
      status: "coming_soon",
      description: "Certificate requests, renewals, and automation are not implemented.",
      action_label: "SSL automation coming soon",
      action_available: false,
    },
    {
      slug: "logs",
      name: "Logs",
      status: "coming_soon",
      description: "Web log browsing and retention controls are placeholder-only.",
      action_label: "Log viewer coming soon",
      action_available: false,
    },
    {
      slug: "php-runtime",
      name: "PHP Runtime",
      status: "unavailable",
      description: "PHP version and pool management are outside this scaffold.",
      action_label: "PHP controls unavailable",
      action_available: false,
    },
  ];
}

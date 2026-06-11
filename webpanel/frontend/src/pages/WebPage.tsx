import {
  Braces,
  FileCode2,
  FileText,
  Globe2,
  Lock,
  Plus,
  ScrollText,
  ServerCog,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  createWebSite,
  disableWebSite,
  getWebStatus,
  listWebSites,
  previewWebSiteNginxConfig,
  type WebSectionStatus,
  type WebSite,
  type WebSiteNginxPreview,
  type WebStatus,
} from "../core/api/web";
import { useAuth } from "../core/auth/AuthProvider";

const sectionIcons = {
  sites: Globe2,
  nginx: ServerCog,
  ssl: ShieldCheck,
  logs: ScrollText,
  "php-runtime": Braces,
};

interface WebPageProps {
  canManageSites: boolean;
  canViewSites: boolean;
  moduleState: string;
}

export function WebPage({ canManageSites, canViewSites, moduleState }: WebPageProps) {
  const { token } = useAuth();
  const [status, setStatus] = useState<WebStatus | null>(null);
  const [sites, setSites] = useState<WebSite[]>([]);
  const [domain, setDomain] = useState("");
  const [rootPath, setRootPath] = useState("");
  const [phpRuntime, setPhpRuntime] = useState("none");
  const [sslEnabled, setSslEnabled] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [siteError, setSiteError] = useState<string | null>(null);
  const [siteMessage, setSiteMessage] = useState<string | null>(null);
  const [nginxPreview, setNginxPreview] = useState<WebSiteNginxPreview | null>(null);
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

  async function loadSites() {
    if (!token || !canViewSites) {
      setSites([]);
      return;
    }

    try {
      setSites(await listWebSites(token));
      setSiteError(null);
    } catch {
      setSiteError("Unable to load Web site registry records.");
    }
  }

  useEffect(() => {
    void loadSites();
  }, [canViewSites, token]);

  async function handleCreateSite() {
    if (!token || !canManageSites) return;

    try {
      const created = await createWebSite(token, {
        domain,
        root_path: rootPath,
        php_runtime: phpRuntime,
        ssl_enabled: sslEnabled,
      });
      setSites((current) => [...current, created].sort((a, b) => a.domain.localeCompare(b.domain)));
      setDomain("");
      setRootPath("");
      setPhpRuntime("none");
      setSslEnabled(false);
      setSiteError(null);
      setSiteMessage(`${created.domain} recorded as config pending. No files or services were changed.`);
    } catch {
      setSiteError("Unable to create Web site record.");
      setSiteMessage(null);
    }
  }

  async function handleDisableSite(siteId: number) {
    if (!token || !canManageSites) return;

    try {
      const disabled = await disableWebSite(token, siteId);
      setSites((current) => current.map((site) => (site.id === disabled.id ? disabled : site)));
      setSiteError(null);
      setSiteMessage(`${disabled.domain} disabled as a registry record only.`);
    } catch {
      setSiteError("Unable to disable Web site record.");
      setSiteMessage(null);
    }
  }

  async function handlePreviewNginxConfig(siteId: number) {
    if (!token || !canViewSites) return;

    try {
      setNginxPreview(await previewWebSiteNginxConfig(token, siteId));
      setSiteError(null);
    } catch {
      setSiteError("Unable to generate Nginx config preview.");
      setNginxPreview(null);
    }
  }

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

      <section className="web-sites-registry" aria-label="Web sites registry">
        <div className="dashboard-section-heading compact">
          <div>
            <span className="eyebrow">Records only</span>
            <h2>Sites</h2>
          </div>
          <span className="section-chip">
            <Lock size={14} />
            Not provisioned yet
          </span>
        </div>

        {siteError ? <div className="login-error">{siteError}</div> : null}
        {siteMessage ? <div className="success-message">{siteMessage}</div> : null}

        <div className="web-site-form">
          <label>
            <span>Domain</span>
            <input
              disabled={!canManageSites}
              onChange={(event) => setDomain(event.target.value)}
              placeholder="example.com"
              value={domain}
            />
          </label>
          <label>
            <span>Root path</span>
            <input
              disabled={!canManageSites}
              onChange={(event) => setRootPath(event.target.value)}
              placeholder="/srv/www/example.com"
              value={rootPath}
            />
          </label>
          <label>
            <span>PHP runtime</span>
            <input
              disabled={!canManageSites}
              onChange={(event) => setPhpRuntime(event.target.value)}
              value={phpRuntime}
            />
          </label>
          <label className="checkbox-row web-ssl-toggle">
            <input
              checked={sslEnabled}
              disabled={!canManageSites}
              onChange={(event) => setSslEnabled(event.target.checked)}
              type="checkbox"
            />
            <span>SSL flag only</span>
          </label>
          <button
            className="primary-button compact"
            disabled={!canManageSites || !domain.trim() || !rootPath.trim()}
            onClick={handleCreateSite}
            type="button"
          >
            <Plus size={16} />
            Add Record
          </button>
        </div>

        <div className="data-table-wrap">
          <table className="data-table web-sites-table">
            <thead>
              <tr>
                <th>Domain</th>
                <th>Status</th>
                <th>Root path</th>
                <th>Runtime</th>
                <th>SSL</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {!canViewSites ? (
                <tr>
                  <td colSpan={6}>
                    <span className="empty-table-note">Web site registry is hidden by RBAC.</span>
                  </td>
                </tr>
              ) : sites.length === 0 ? (
                <tr>
                  <td colSpan={6}>
                    <span className="empty-table-note">No Web site records exist yet.</span>
                  </td>
                </tr>
              ) : (
                sites.map((site) => (
                  <tr key={site.id}>
                    <td>
                      <strong>{site.domain}</strong>
                      <span>not provisioned yet</span>
                    </td>
                    <td>
                      <span className={`state-pill web-site-status ${site.status}`}>
                        <Lock size={14} />
                        {site.status === "config_pending" ? "Config pending" : site.status}
                      </span>
                    </td>
                    <td>
                      <code className="path-code">{site.root_path}</code>
                    </td>
                    <td>{site.php_runtime}</td>
                    <td>{site.ssl_enabled ? "Flagged" : "Off"}</td>
                    <td>
                      <div className="web-site-actions">
                        <button
                          className="icon-text-button"
                          disabled={!canViewSites}
                          onClick={() => handlePreviewNginxConfig(site.id)}
                          type="button"
                        >
                          <FileCode2 size={15} />
                          Preview Nginx Config
                        </button>
                        <button
                          className="icon-text-button state-disabled"
                          disabled={!canManageSites || site.status === "disabled"}
                          onClick={() => handleDisableSite(site.id)}
                          type="button"
                        >
                          <Lock size={15} />
                          Disable record
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      {nginxPreview ? (
        <div className="modal-backdrop" role="presentation">
          <section className="confirm-modal nginx-preview-modal" aria-label="Nginx config preview">
            <div>
              <span className="eyebrow">Preview only</span>
              <h2>Nginx config</h2>
            </div>
            <p>
              Generated for {nginxPreview.domain}. This text was not saved, tested, reloaded, or
              applied to the server.
            </p>
            <pre className="config-preview-block">
              <code>{nginxPreview.config}</code>
            </pre>
            <div className="modal-actions">
              <button
                className="icon-text-button"
                onClick={() => setNginxPreview(null)}
                type="button"
              >
                Close
              </button>
            </div>
          </section>
        </div>
      ) : null}
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

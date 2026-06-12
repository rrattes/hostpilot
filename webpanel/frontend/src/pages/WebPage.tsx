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
  applyWebSiteNginxConfig,
  createWebSite,
  disableWebSite,
  disableWebSiteNginxConfig,
  getWebSiteNginxApplyPlan,
  getWebSiteReadiness,
  getWebStatus,
  listWebSites,
  markWebSiteReadyToApply,
  previewWebSiteNginxConfig,
  reapplyWebSiteNginxConfig,
  runWebSiteNginxDryRun,
  type ProvisioningStatus,
  type WebSectionStatus,
  type WebSite,
  type WebSiteApplyResult,
  type WebSiteDisableResult,
  type WebSiteDryRunResult,
  type WebSiteNginxApplyPlan,
  type WebSiteNginxPreview,
  type WebSiteReadiness,
  type WebSiteReapplyResult,
  type WebStatus,
} from "../core/api/web";
import { ApiError } from "../core/api/client";
import { useAuth } from "../core/auth/AuthProvider";

const sectionIcons = {
  sites: Globe2,
  nginx: ServerCog,
  ssl: ShieldCheck,
  logs: ScrollText,
  "php-runtime": Braces,
};
const defaultSitesBasePath = "/var/www/hostpilot-sites";

interface WebPageProps {
  canManageSites: boolean;
  canViewSites: boolean;
  moduleState: string;
}

export function WebPage({ canManageSites, canViewSites, moduleState }: WebPageProps) {
  const { token } = useAuth();
  const [status, setStatus] = useState<WebStatus | null>(null);
  const [sites, setSites] = useState<WebSite[]>([]);
  const [readinessBySiteId, setReadinessBySiteId] = useState<Record<number, WebSiteReadiness>>({});
  const [domain, setDomain] = useState("");
  const [rootPath, setRootPath] = useState("");
  const [phpRuntime, setPhpRuntime] = useState("none");
  const [sslEnabled, setSslEnabled] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [siteError, setSiteError] = useState<string | null>(null);
  const [siteMessage, setSiteMessage] = useState<string | null>(null);
  const [nginxPreview, setNginxPreview] = useState<WebSiteNginxPreview | null>(null);
  const [applyPlan, setApplyPlan] = useState<WebSiteNginxApplyPlan | null>(null);
  const [dryRunPhrase, setDryRunPhrase] = useState("");
  const [dryRunResult, setDryRunResult] = useState<WebSiteDryRunResult | null>(null);
  const [applyPhrase, setApplyPhrase] = useState("");
  const [applyResult, setApplyResult] = useState<WebSiteApplyResult | null>(null);
  const [disableTarget, setDisableTarget] = useState<WebSite | null>(null);
  const [disablePhrase, setDisablePhrase] = useState("");
  const [disableResult, setDisableResult] = useState<WebSiteDisableResult | null>(null);
  const [reapplyTarget, setReapplyTarget] = useState<WebSite | null>(null);
  const [reapplyPhrase, setReapplyPhrase] = useState("");
  const [reapplyResult, setReapplyResult] = useState<WebSiteReapplyResult | null>(null);
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
      const response = await listWebSites(token);
      setSites(response);
      await loadReadiness(response);
      setSiteError(null);
    } catch {
      setSiteError("Unable to load Web site registry records.");
    }
  }

  useEffect(() => {
    void loadSites();
  }, [canViewSites, token]);

  async function loadReadiness(siteRecords: WebSite[]) {
    if (!token || !canViewSites || siteRecords.length === 0) {
      setReadinessBySiteId({});
      return;
    }

    const entries = await Promise.all(
      siteRecords.map(async (site) => [site.id, await getWebSiteReadiness(token, site.id)] as const),
    );
    setReadinessBySiteId(Object.fromEntries(entries));
  }

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
      const readiness = await getWebSiteReadiness(token, created.id);
      setReadinessBySiteId((current) => ({ ...current, [created.id]: readiness }));
      setDomain("");
      setRootPath("");
      setPhpRuntime("none");
      setSslEnabled(false);
      setSiteError(null);
      setSiteMessage(`${created.domain} recorded as config pending. No files or services were changed.`);
    } catch (createError) {
      setSiteError(
        createError instanceof ApiError
          ? createError.message
          : "Unable to create Web site record.",
      );
      setSiteMessage(null);
    }
  }

  async function handleDisableSite(siteId: number) {
    if (!token || !canManageSites) return;

    try {
      const disabled = await disableWebSite(token, siteId);
      setSites((current) => current.map((site) => (site.id === disabled.id ? disabled : site)));
      const readiness = await getWebSiteReadiness(token, disabled.id);
      setReadinessBySiteId((current) => ({ ...current, [disabled.id]: readiness }));
      setSiteError(null);
      setSiteMessage(`${disabled.domain} disabled as a registry record only.`);
    } catch (disableError) {
      setSiteError(
        disableError instanceof ApiError
          ? disableError.message
          : "Unable to disable Web site record.",
      );
      setSiteMessage(null);
    }
  }

  async function handlePreviewNginxConfig(siteId: number) {
    if (!token || !canViewSites) return;

    try {
      setNginxPreview(await previewWebSiteNginxConfig(token, siteId));
      const readiness = await getWebSiteReadiness(token, siteId);
      setReadinessBySiteId((current) => ({ ...current, [siteId]: readiness }));
      setSites((current) =>
        current.map((site) =>
          site.id === siteId ? { ...site, provisioning_status: readiness.provisioning_status } : site,
        ),
      );
      setSiteError(null);
    } catch (previewError) {
      setSiteError(
        previewError instanceof ApiError
          ? previewError.message
          : "Unable to generate Nginx config preview.",
      );
      setNginxPreview(null);
    }
  }

  async function handleMarkReady(siteId: number) {
    if (!token || !canManageSites) return;

    try {
      const readySite = await markWebSiteReadyToApply(token, siteId);
      setSites((current) => current.map((site) => (site.id === readySite.id ? readySite : site)));
      const readiness = await getWebSiteReadiness(token, siteId);
      setReadinessBySiteId((current) => ({ ...current, [siteId]: readiness }));
      setSiteError(null);
      setSiteMessage(`${readySite.domain} is ready to apply. No server changes were made.`);
    } catch (readyError) {
      setSiteError(
        readyError instanceof ApiError
          ? readyError.message
          : "Unable to mark Web site ready to apply.",
      );
      setSiteMessage(null);
    }
  }

  async function handleViewApplyPlan(siteId: number) {
    if (!token || !canViewSites) return;

    try {
      setApplyPlan(await getWebSiteNginxApplyPlan(token, siteId));
      setDryRunPhrase("");
      setDryRunResult(null);
      setApplyPhrase("");
      setApplyResult(null);
      setSiteError(null);
    } catch (planError) {
      setSiteError(
        planError instanceof ApiError
          ? planError.message
          : "Unable to generate Nginx apply plan.",
      );
      setApplyPlan(null);
    }
  }

  async function handleRunDryRun() {
    if (!token || !applyPlan) return;

    try {
      const result = await runWebSiteNginxDryRun(token, applyPlan.site_id, dryRunPhrase);
      setDryRunResult(result);
      setSiteError(null);
      setSiteMessage(`${result.domain} dry-run completed. No files, commands, or services changed.`);
    } catch (dryRunError) {
      setSiteError(
        dryRunError instanceof ApiError
          ? dryRunError.message
          : "Unable to run Nginx dry-run.",
      );
      setDryRunResult(null);
    }
  }

  async function handleApplyNginxConfig() {
    if (!token || !applyPlan || !canManageSites) return;

    try {
      const result = await applyWebSiteNginxConfig(token, applyPlan.site_id, applyPhrase);
      setApplyResult(result);
      setSites((current) => current.map((site) => (site.id === result.site.id ? result.site : site)));
      setSiteError(null);
      setSiteMessage(
        result.success
          ? `${result.site.domain} applied through controlled Agent job #${result.job_id}.`
          : `${result.site.domain} apply failed through Agent job #${result.job_id}.`,
      );
    } catch (applyError) {
      setSiteError(
        applyError instanceof ApiError
          ? applyError.message
          : "Unable to apply Nginx config.",
      );
      setApplyResult(null);
    }
  }

  async function handleDisableNginxConfig() {
    if (!token || !disableTarget || !canManageSites) return;

    try {
      const result = await disableWebSiteNginxConfig(token, disableTarget.id, disablePhrase);
      setDisableResult(result);
      setSites((current) => current.map((site) => (site.id === result.site.id ? result.site : site)));
      const readiness = await getWebSiteReadiness(token, result.site.id);
      setReadinessBySiteId((current) => ({ ...current, [result.site.id]: readiness }));
      setSiteError(null);
      setSiteMessage(
        result.success
          ? `${result.site.domain} disabled through controlled Agent job #${result.job_id}.`
          : `${result.site.domain} disable failed through Agent job #${result.job_id}.`,
      );
    } catch (disableError) {
      setSiteError(
        disableError instanceof ApiError
          ? disableError.message
          : "Unable to disable Nginx config.",
      );
      setDisableResult(null);
    }
  }

  function openDisableModal(site: WebSite) {
    setDisableTarget(site);
    setDisablePhrase("");
    setDisableResult(null);
    setSiteError(null);
  }

  async function handleReapplyNginxConfig() {
    if (!token || !reapplyTarget || !canManageSites) return;

    try {
      const result = await reapplyWebSiteNginxConfig(token, reapplyTarget.id, reapplyPhrase);
      setReapplyResult(result);
      setSites((current) => current.map((site) => (site.id === result.site.id ? result.site : site)));
      const readiness = await getWebSiteReadiness(token, result.site.id);
      setReadinessBySiteId((current) => ({ ...current, [result.site.id]: readiness }));
      setSiteError(null);
      setSiteMessage(
        result.success
          ? `${result.site.domain} re-applied through controlled Agent job #${result.job_id}.`
          : `${result.site.domain} re-apply failed through Agent job #${result.job_id}.`,
      );
    } catch (reapplyError) {
      setSiteError(
        reapplyError instanceof ApiError
          ? reapplyError.message
          : "Unable to re-apply Nginx config.",
      );
      setReapplyResult(null);
    }
  }

  function openReapplyModal(site: WebSite) {
    setReapplyTarget(site);
    setReapplyPhrase("");
    setReapplyResult(null);
    setSiteError(null);
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
            This page manages Web site records and controlled Nginx workflows only. SSL, PHP
            management, log browsing, deploy changes, and arbitrary Agent actions remain disabled.
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
          <p>Only controlled HostPilot Nginx apply and disable workflows are available.</p>
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
              placeholder={`${defaultSitesBasePath}/example.com`}
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
        <div className="web-validation-note">
          New records must use a valid domain and a safe absolute root path under{" "}
          <code>{defaultSitesBasePath}</code>. Validation only affects registry records.
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
                <th>Readiness</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {!canViewSites ? (
                <tr>
                  <td colSpan={7}>
                    <span className="empty-table-note">Web site registry is hidden by RBAC.</span>
                  </td>
                </tr>
              ) : sites.length === 0 ? (
                <tr>
                  <td colSpan={7}>
                    <span className="empty-table-note">No Web site records exist yet.</span>
                  </td>
                </tr>
              ) : (
                sites.map((site) => (
                  <tr key={site.id}>
                    <td>
                      <strong>{site.domain}</strong>
                      <span>not provisioned yet</span>
                      <span className={`workflow-badge ${site.provisioning_status}`}>
                        {workflowLabel(site.provisioning_status)}
                      </span>
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
                      <ReadinessChecklist readiness={readinessBySiteId[site.id]} />
                    </td>
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
                          className="icon-text-button"
                          disabled={!canManageSites || !readinessBySiteId[site.id]?.ready}
                          onClick={() => handleMarkReady(site.id)}
                          type="button"
                        >
                          <ShieldCheck size={15} />
                          Mark Ready
                        </button>
                        <button
                          className="icon-text-button"
                          disabled={!canViewSites || site.provisioning_status !== "ready_to_apply"}
                          onClick={() => handleViewApplyPlan(site.id)}
                          type="button"
                        >
                          <FileText size={15} />
                          View Apply Plan
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
                        <button
                          className="icon-text-button state-disabled"
                          disabled={!canManageSites || site.status !== "applied"}
                          onClick={() => openDisableModal(site)}
                          type="button"
                        >
                          <Lock size={15} />
                          Disable Site
                        </button>
                        <button
                          className="icon-text-button"
                          disabled={!canManageSites || !["disabled", "error"].includes(site.status)}
                          onClick={() => openReapplyModal(site)}
                          type="button"
                        >
                          <ShieldCheck size={15} />
                          Enable/Re-Apply
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

      {applyPlan ? (
        <div className="modal-backdrop" role="presentation">
          <section className="confirm-modal nginx-preview-modal" aria-label="Nginx apply plan">
            <div>
              <span className="eyebrow">Plan only</span>
              <h2>Nginx apply plan</h2>
            </div>
            <p>
              Generated for {applyPlan.domain}. No files were written, no directories were created,
              and no commands were run.
            </p>
            <div className="apply-plan-grid">
              <PlanFact label="Target config path" value={applyPlan.target_config_path} />
              <PlanFact label="Webroot path" value={applyPlan.webroot_path} />
              <PlanFact label="Config filename" value={applyPlan.config_filename} />
              <PlanFact label="Risk level" value={applyPlan.risk_level} />
              <PlanFact label="Future confirmation" value={applyPlan.confirmation_phrase} wide />
            </div>
            <div className="apply-plan-section">
              <strong>Required directories</strong>
              {applyPlan.required_directories.map((directory) => (
                <code className="path-code" key={directory}>{directory}</code>
              ))}
            </div>
            <div className="apply-plan-section">
              <strong>Validation commands for a future apply</strong>
              {applyPlan.validation_commands.map((command) => (
                <code className="path-code" key={command}>{command}</code>
              ))}
            </div>
            <div className="apply-plan-section">
              <strong>Future service reload command</strong>
              <code className="path-code">{applyPlan.service_reload_command}</code>
            </div>
            <label className="dry-run-confirmation">
              <span>Dry-run confirmation phrase</span>
              <input
                onChange={(event) => setDryRunPhrase(event.target.value)}
                placeholder={applyPlan.confirmation_phrase}
                value={dryRunPhrase}
              />
            </label>
            <button
              className="primary-button compact"
              disabled={dryRunPhrase !== applyPlan.confirmation_phrase}
              onClick={handleRunDryRun}
              type="button"
            >
              Run Dry-Run
            </button>
            {dryRunResult ? <DryRunResultPanel result={dryRunResult} /> : null}
            <div className="web-apply-warning">
              <strong>Controlled Agent apply</strong>
              <span>
                This action asks the local Agent to create only the approved webroot, write one
                HostPilot Nginx config, run nginx -t, and reload Nginx only if validation passes.
              </span>
            </div>
            <label className="dry-run-confirmation">
              <span>Apply confirmation phrase</span>
              <input
                onChange={(event) => setApplyPhrase(event.target.value)}
                placeholder={applyPlan.confirmation_phrase}
                value={applyPhrase}
              />
            </label>
            <button
              className="primary-button compact"
              disabled={!canManageSites || applyPhrase !== applyPlan.confirmation_phrase}
              onClick={handleApplyNginxConfig}
              type="button"
            >
              Apply Nginx Config
            </button>
            {applyResult ? <ApplyResultPanel result={applyResult} /> : null}
            <div className="modal-actions">
              <button
                className="icon-text-button"
                onClick={() => {
                  setApplyPlan(null);
                  setDryRunPhrase("");
                  setDryRunResult(null);
                  setApplyPhrase("");
                  setApplyResult(null);
                }}
                type="button"
              >
                Close
              </button>
            </div>
          </section>
        </div>
      ) : null}

      {disableTarget ? (
        <div className="modal-backdrop" role="presentation">
          <section className="confirm-modal nginx-preview-modal" aria-label="Disable Nginx site">
            <div>
              <span className="eyebrow">Controlled Agent disable</span>
              <h2>Disable site</h2>
            </div>
            <p>
              This removes only the HostPilot-managed config for {disableTarget.domain}, runs nginx
              -t, and reloads Nginx only if validation passes. If validation fails, the removed
              config is restored.
            </p>
            <div className="web-apply-warning">
              <strong>Required confirmation</strong>
              <span>{disableConfirmationPhrase(disableTarget)}</span>
            </div>
            <label className="dry-run-confirmation">
              <span>Disable confirmation phrase</span>
              <input
                onChange={(event) => setDisablePhrase(event.target.value)}
                placeholder={disableConfirmationPhrase(disableTarget)}
                value={disablePhrase}
              />
            </label>
            <button
              className="primary-button compact"
              disabled={
                !canManageSites || disablePhrase !== disableConfirmationPhrase(disableTarget)
              }
              onClick={handleDisableNginxConfig}
              type="button"
            >
              Disable Site
            </button>
            {disableResult ? <AgentResultPanel result={disableResult} mode="disable" /> : null}
            <div className="modal-actions">
              <button
                className="icon-text-button"
                onClick={() => {
                  setDisableTarget(null);
                  setDisablePhrase("");
                  setDisableResult(null);
                }}
                type="button"
              >
                Close
              </button>
            </div>
          </section>
        </div>
      ) : null}

      {reapplyTarget ? (
        <div className="modal-backdrop" role="presentation">
          <section className="confirm-modal nginx-preview-modal" aria-label="Enable or re-apply Nginx site">
            <div>
              <span className="eyebrow">Controlled Agent re-apply</span>
              <h2>Enable/Re-Apply site</h2>
            </div>
            <p>
              This reuses the controlled apply flow for {reapplyTarget.domain}. The Agent may only
              create the approved webroot, write the one HostPilot-managed Nginx config, run nginx
              -t, and reload Nginx if validation passes.
            </p>
            <div className="web-apply-warning">
              <strong>Required confirmation</strong>
              <span>{applyConfirmationPhrase(reapplyTarget)}</span>
            </div>
            <label className="dry-run-confirmation">
              <span>Enable/Re-Apply confirmation phrase</span>
              <input
                onChange={(event) => setReapplyPhrase(event.target.value)}
                placeholder={applyConfirmationPhrase(reapplyTarget)}
                value={reapplyPhrase}
              />
            </label>
            <button
              className="primary-button compact"
              disabled={!canManageSites || reapplyPhrase !== applyConfirmationPhrase(reapplyTarget)}
              onClick={handleReapplyNginxConfig}
              type="button"
            >
              Enable/Re-Apply Site
            </button>
            {reapplyResult ? <AgentResultPanel result={reapplyResult} mode="re-apply" /> : null}
            <div className="modal-actions">
              <button
                className="icon-text-button"
                onClick={() => {
                  setReapplyTarget(null);
                  setReapplyPhrase("");
                  setReapplyResult(null);
                }}
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

function ApplyResultPanel({ result }: { result: WebSiteApplyResult }) {
  return <AgentResultPanel result={result} mode="apply" />;
}

function AgentResultPanel({
  result,
  mode,
}: {
  result: WebSiteApplyResult | WebSiteDisableResult;
  mode: "apply" | "disable" | "re-apply";
}) {
  return (
    <div className={`dry-run-result ${result.success ? "" : "failed"}`}>
      <strong>Agent job #{result.job_id}</strong>
      <span>
        {result.success
          ? `Controlled ${mode} completed.`
          : result.error ?? `Controlled ${mode} failed.`}
      </span>
      <div className="apply-plan-section">
        <strong>Agent status</strong>
        <code className="path-code">{result.status}</code>
        <code className="path-code">{result.site.status}</code>
      </div>
      <pre className="config-preview-block">
        <code>{JSON.stringify(result.result, null, 2)}</code>
      </pre>
    </div>
  );
}

function disableConfirmationPhrase(site: WebSite) {
  return `DISABLE NGINX SITE ${site.domain}`;
}

function applyConfirmationPhrase(site: WebSite) {
  return `APPLY NGINX PLAN ${site.domain}`;
}

function DryRunResultPanel({ result }: { result: WebSiteDryRunResult }) {
  return (
    <div className="dry-run-result">
      <strong>Dry-run result</strong>
      <span>{result.expected_result}</span>
      <div className="apply-plan-section">
        <strong>Target paths</strong>
        <code className="path-code">{result.target_config_path}</code>
        <code className="path-code">{result.webroot_path}</code>
      </div>
      <div className="apply-plan-section">
        <strong>Directory checks</strong>
        {result.directory_checks.map((check) => (
          <code className="path-code" key={check}>{check}</code>
        ))}
      </div>
      <div className="apply-plan-section">
        <strong>Simulated commands</strong>
        <code className="path-code">{result.nginx_validation_command}</code>
        <code className="path-code">{result.reload_command}</code>
      </div>
      <pre className="config-preview-block">
        <code>{result.config_content}</code>
      </pre>
    </div>
  );
}

function PlanFact({ label, value, wide = false }: { label: string; value: string; wide?: boolean }) {
  return (
    <div className={`apply-plan-fact ${wide ? "wide" : ""}`}>
      <span>{label}</span>
      <code>{value}</code>
    </div>
  );
}

function ReadinessChecklist({ readiness }: { readiness?: WebSiteReadiness }) {
  if (!readiness) {
    return <span className="empty-table-note">Readiness loading.</span>;
  }

  return (
    <div className="readiness-list">
      {readiness.checks.map((check) => (
        <span className={`readiness-check ${check.passed ? "passed" : "failed"}`} key={check.slug}>
          {check.label}
        </span>
      ))}
    </div>
  );
}

function workflowLabel(status: ProvisioningStatus) {
  const labels: Record<ProvisioningStatus, string> = {
    draft: "Draft",
    config_previewed: "Previewed",
    ready_to_apply: "Ready to Apply",
    disabled: "Disabled",
    error: "Error",
  };
  return labels[status];
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

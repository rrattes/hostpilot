import {
  ChevronDown,
  File,
  FileCode2,
  FileText,
  FolderOpen,
  Globe2,
  Lock,
  Plus,
  RefreshCw,
  ScrollText,
  ServerCog,
  ShieldAlert,
  ShieldCheck,
  MoreHorizontal,
} from "lucide-react";
import { Fragment, useEffect, useMemo, useState } from "react";

import {
  applyWebSiteNginxConfig,
  createWebSite,
  disableWebSite,
  disableWebSiteNginxConfig,
  getWebSiteNginxApplyPlan,
  getWebSiteFiles,
  getWebSiteLogs,
  getWebSiteReadiness,
  getWebSitePreflight,
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
  type WebSiteFileEntry,
  type WebSiteFiles,
  type WebSiteLogFile,
  type WebSiteLogs,
  type WebSiteNginxApplyPlan,
  type WebSitePreflight,
  type WebSiteNginxPreview,
  type WebSiteReadiness,
  type WebSiteReapplyResult,
  type WebStatus,
} from "../core/api/web";
import type { AgentStatus } from "../core/api/agent";
import { apiErrorMessage } from "../core/api/client";
import { useAuth } from "../core/auth/AuthProvider";

const defaultSitesBasePath = "/var/www/hostpilot-sites";

interface WebPageProps {
  agentStatus: AgentStatus | null;
  canManageSites: boolean;
  canViewSites: boolean;
  moduleState: string;
}

export function WebPage({ agentStatus, canManageSites, canViewSites, moduleState }: WebPageProps) {
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
  const [isCreatingSite, setIsCreatingSite] = useState(false);
  const [nginxPreview, setNginxPreview] = useState<WebSiteNginxPreview | null>(null);
  const [applyPlan, setApplyPlan] = useState<WebSiteNginxApplyPlan | null>(null);
  const [preflight, setPreflight] = useState<WebSitePreflight | null>(null);
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
  const [logsTarget, setLogsTarget] = useState<WebSite | null>(null);
  const [logsResult, setLogsResult] = useState<WebSiteLogs | null>(null);
  const [logsLoading, setLogsLoading] = useState(false);
  const [filesTarget, setFilesTarget] = useState<WebSite | null>(null);
  const [filesResult, setFilesResult] = useState<WebSiteFiles | null>(null);
  const [filesError, setFilesError] = useState<string | null>(null);
  const [filesLoading, setFilesLoading] = useState(false);
  const [filesSubpath, setFilesSubpath] = useState("");
  const [filesPage, setFilesPage] = useState(1);
  const [expandedSiteId, setExpandedSiteId] = useState<number | null>(null);
  const sections = useMemo(() => status?.sections ?? fallbackSections(), [status]);
  const sectionBySlug = useMemo(
    () => Object.fromEntries(sections.map((section) => [section.slug, section])),
    [sections],
  );
  const realAgentAvailable =
    agentStatus?.status === "connected" && agentStatus.web_actions_use_real_agent;
  const agentControlMessage = agentStatus
    ? agentStatus.message
    : "Agent status is still loading. Controlled Nginx actions require a connected Agent.";

  useEffect(() => {
    if (!token) return;

    getWebStatus(token)
      .then((response) => {
        setStatus(response);
        setError(null);
      })
      .catch((loadError) =>
        setError(apiErrorMessage(loadError, "Unable to load Web module scaffold status.")),
      );
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
    } catch (loadError) {
      setSiteError(apiErrorMessage(loadError, "Unable to load Web site registry records."));
    }
  }

  useEffect(() => {
    void loadSites();
  }, [canViewSites, token]);

  useEffect(() => {
    if (!filesTarget) return;

    setFilesResult(null);
    setFilesError(null);
    setFilesSubpath("");
    setFilesPage(1);
    void refreshFiles(filesTarget, "", 1);
  }, [filesTarget?.id, token, canViewSites]);

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
    if (!token || !canManageSites || isCreatingSite) return;
    const nextDomain = domain.trim();
    const nextRootPath = rootPath.trim();
    if (!nextDomain || !nextRootPath) {
      setSiteError("Enter a domain and root path before adding a Web site record.");
      setSiteMessage(null);
      return;
    }

    try {
      setIsCreatingSite(true);
      const created = await createWebSite(token, {
        domain: nextDomain,
        root_path: nextRootPath,
        php_runtime: phpRuntime.trim() || "none",
        ssl_enabled: sslEnabled,
      });
      setDomain("");
      setRootPath("");
      setPhpRuntime("none");
      setSslEnabled(false);
      setSiteError(null);
      setSiteMessage(`${created.domain} recorded as config pending. No files or services were changed.`);
      await loadSites();
    } catch (createError) {
      setSiteError(apiErrorMessage(createError, "Unable to create Web site record."));
      setSiteMessage(null);
    } finally {
      setIsCreatingSite(false);
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
      setSiteError(apiErrorMessage(disableError, "Unable to disable Web site record."));
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
      setSiteError(apiErrorMessage(previewError, "Unable to generate Nginx config preview."));
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
      setSiteError(apiErrorMessage(readyError, "Unable to mark Web site ready to apply."));
      setSiteMessage(null);
    }
  }

  async function handleViewApplyPlan(siteId: number) {
    if (!token || !canViewSites) return;

    try {
      setPreflight(null);
      const [plan, preflightResult] = await Promise.all([
        getWebSiteNginxApplyPlan(token, siteId),
        getWebSitePreflight(token, siteId),
      ]);
      setApplyPlan(plan);
      setPreflight(preflightResult);
      setDryRunPhrase("");
      setDryRunResult(null);
      setApplyPhrase("");
      setApplyResult(null);
      setSiteError(null);
    } catch (planError) {
      setSiteError(apiErrorMessage(planError, "Unable to generate Nginx apply plan."));
      setApplyPlan(null);
      setPreflight(null);
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
      setSiteError(apiErrorMessage(dryRunError, "Unable to run Nginx dry-run."));
      setDryRunResult(null);
    }
  }

  async function handleApplyNginxConfig() {
    if (!token || !applyPlan || !canManageSites || !realAgentAvailable) return;

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
      setSiteError(apiErrorMessage(applyError, "Unable to apply Nginx config."));
      setApplyResult(null);
    }
  }

  async function handleDisableNginxConfig() {
    if (!token || !disableTarget || !canManageSites || !realAgentAvailable) return;

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
      setSiteError(apiErrorMessage(disableError, "Unable to disable Nginx config."));
      setDisableResult(null);
    }
  }

  function openDisableModal(site: WebSite) {
    setDisableTarget(site);
    setDisablePhrase("");
    setDisableResult(null);
    setSiteError(null);
    setPreflight(null);
    void loadPreflight(site.id);
  }

  async function handleReapplyNginxConfig() {
    if (!token || !reapplyTarget || !canManageSites || !realAgentAvailable) return;

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
      setSiteError(apiErrorMessage(reapplyError, "Unable to re-apply Nginx config."));
      setReapplyResult(null);
    }
  }

  function openReapplyModal(site: WebSite) {
    setReapplyTarget(site);
    setReapplyPhrase("");
    setReapplyResult(null);
    setSiteError(null);
    setPreflight(null);
    void loadPreflight(site.id);
  }

  async function loadPreflight(siteId: number) {
    if (!token || !canViewSites) return;

    try {
      setPreflight(await getWebSitePreflight(token, siteId));
      setSiteError(null);
    } catch (preflightError) {
      setPreflight(null);
      setSiteError(apiErrorMessage(preflightError, "Unable to load Web Agent preflight."));
    }
  }

  async function handleViewLogs(site: WebSite) {
    setLogsTarget(site);
    await refreshLogs(site);
  }

  async function refreshLogs(site = logsTarget) {
    if (!token || !site || !canViewSites) return;

    try {
      setLogsLoading(true);
      setLogsResult(await getWebSiteLogs(token, site.id, 100));
      setSiteError(null);
    } catch (logsError) {
      setSiteError(apiErrorMessage(logsError, "Unable to load Web site logs."));
      setLogsResult(null);
    } finally {
      setLogsLoading(false);
    }
  }

  async function handleViewFiles(site: WebSite) {
    setFilesTarget(site);
  }

  async function refreshFiles(site = filesTarget, subpath = filesSubpath, page = filesPage) {
    if (!token || !site || !canViewSites) return;

    try {
      setFilesLoading(true);
      const result = await getWebSiteFiles(token, site.id, subpath, page, 50);
      setFilesResult(result);
      setFilesSubpath(result.relative_subpath);
      setFilesPage(result.page);
      setFilesError(null);
      setSiteError(null);
    } catch (filesError) {
      setFilesError(apiErrorMessage(filesError, "Unable to load Web site files."));
      setFilesResult(null);
    } finally {
      setFilesLoading(false);
    }
  }

  function navigateFiles(subpath: string, page = 1) {
    setFilesSubpath(subpath);
    setFilesPage(page);
    void refreshFiles(filesTarget, subpath, page);
  }

  const appliedSites = sites.filter((site) => site.status === "applied").length;
  const readySites = sites.filter((site) => site.provisioning_status === "ready_to_apply").length;
  const blockedReadiness = sites.filter((site) => readinessBySiteId[site.id]?.ready === false).length;
  const logsAvailable = sectionBySlug.logs?.status === "available";
  const createDomain = domain.trim();
  const createRootPath = rootPath.trim();
  const canSubmitSiteRecord =
    canManageSites && createDomain.length > 0 && createRootPath.length > 0 && !isCreatingSite;
  const createDisabledReason = !canManageSites
    ? "Requires the web.sites.manage permission."
    : !createDomain || !createRootPath
      ? "Enter a domain and root path first."
      : undefined;

  return (
    <section className="data-page web-page" aria-label="Web module">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Web module</span>
          <h2>Web</h2>
          <p className="section-subtitle">Site records, read-only Files/Logs, and controlled Nginx workflows.</p>
        </div>
        <div className="page-actions">
          <span className="count-pill">
            <ShieldCheck size={14} />
            {status?.module_state ?? moduleState}
          </span>
          <span className="count-pill">
            <ShieldAlert size={14} />
            {realAgentAvailable ? "Agent connected" : "Agent not connected"}
          </span>
        </div>
      </div>

      {error ? <div className="login-error">{error}</div> : null}

      <div className="web-status-grid">
        <div className="summary-panel summary-panel-primary">
          <div className="summary-panel-header">
            <span className="summary-icon">
              <Globe2 size={17} />
            </span>
            <span className="metric-label">Sites</span>
          </div>
          <strong>{sites.length}</strong>
          <p>{appliedSites} applied, {readySites} ready to apply.</p>
        </div>
        <div className="summary-panel">
          <div className="summary-panel-header">
            <span className="summary-icon">
              <ServerCog size={17} />
            </span>
            <span className="metric-label">Nginx</span>
          </div>
          <strong>{realAgentAvailable ? "Ready" : "Blocked"}</strong>
          <p>{realAgentAvailable ? "Controlled Apply/Disable/Re-Apply available." : agentControlMessage}</p>
        </div>
        <div className="summary-panel">
          <div className="summary-panel-header">
            <span className="summary-icon">
              <FolderOpen size={17} />
            </span>
            <span className="metric-label">Logs/Files</span>
          </div>
          <strong>{logsAvailable ? "Read-only" : "Limited"}</strong>
          <p>{blockedReadiness} site readiness checks need attention. SSL/PHP remain low-priority flags.</p>
        </div>
      </div>

      <section className="web-sites-registry" aria-label="Web sites registry">
        <div className="dashboard-section-heading compact">
          <div>
            <span className="eyebrow">Primary workflow</span>
            <h2>Sites</h2>
          </div>
          <span className="section-chip">
            <Lock size={14} />
            Records and controlled actions
          </span>
        </div>

        {siteError ? <div className="login-error">{siteError}</div> : null}
        {siteMessage ? <div className="success-message">{siteMessage}</div> : null}

        {canManageSites ? (
          <>
            <div className="web-site-form">
              <label>
                <span>Domain</span>
                <input
                  disabled={isCreatingSite}
                  onChange={(event) => setDomain(event.target.value)}
                  placeholder="example.com"
                  value={domain}
                />
              </label>
              <label>
                <span>Root path</span>
                <input
                  disabled={isCreatingSite}
                  onChange={(event) => setRootPath(event.target.value)}
                  placeholder={`${defaultSitesBasePath}/example.com`}
                  value={rootPath}
                />
              </label>
              <label>
                <span>PHP runtime</span>
                <input
                  disabled={isCreatingSite}
                  onChange={(event) => setPhpRuntime(event.target.value)}
                  value={phpRuntime}
                />
              </label>
              <label className="checkbox-row web-ssl-toggle">
                <input
                  checked={sslEnabled}
                  disabled={isCreatingSite}
                  onChange={(event) => setSslEnabled(event.target.checked)}
                  type="checkbox"
                />
                <span>SSL flag only</span>
              </label>
              <button
                aria-busy={isCreatingSite}
                className={`primary-button compact ${isCreatingSite ? "is-loading" : ""}`}
                disabled={!canSubmitSiteRecord}
                onClick={handleCreateSite}
                title={createDisabledReason}
                type="button"
              >
                <Plus size={16} />
                {isCreatingSite ? "Adding..." : "Add Record"}
              </button>
            </div>
            <div className="web-validation-note">
              Use a valid domain and a safe absolute root path under <code>{defaultSitesBasePath}</code>.
              SSL/PHP are recorded as metadata only.
            </div>
          </>
        ) : (
          <div className="web-permission-note">
            <Lock size={15} />
            <span>Add Record requires the web.sites.manage permission.</span>
          </div>
        )}

        {!canViewSites ? (
          <div className="web-permission-note">
            <Lock size={15} />
            <span>Web site records are hidden because this user lacks web.sites.view.</span>
          </div>
        ) : (
          <div className="data-table-wrap">
            <table className="data-table web-sites-table">
              <thead>
                <tr>
                  <th>Site</th>
                  <th>Status</th>
                  <th>Readiness</th>
                  <th>Agent</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {sites.length === 0 ? (
                  <tr>
                    <td colSpan={5}>
                      <span className="empty-table-note">
                        Create a site record to access Files, Logs, and Nginx actions.
                      </span>
                    </td>
                  </tr>
                ) : (
                  sites.map((site) => (
                    <Fragment key={site.id}>
                      <tr key={site.id}>
                        <td>
                          <div className="web-site-title-cell">
                            <button
                              className={`web-row-expand ${expandedSiteId === site.id ? "expanded" : ""}`}
                              onClick={() =>
                                setExpandedSiteId((current) => (current === site.id ? null : site.id))
                              }
                              type="button"
                              aria-label={`Toggle details for ${site.domain}`}
                            >
                              <ChevronDown size={15} />
                            </button>
                            <div>
                              <strong>{site.domain}</strong>
                              <span>{siteSummaryLabel(site)}</span>
                            </div>
                          </div>
                        </td>
                        <td>
                          <SiteStatusSummary site={site} />
                        </td>
                        <td>
                          <ReadinessSummary readiness={readinessBySiteId[site.id]} />
                        </td>
                        <td>
                          <AgentStateChip agentStatus={agentStatus} realAgentAvailable={realAgentAvailable} />
                        </td>
                        <td>
                          <SiteActionsMenu
                            canManageSites={canManageSites}
                            canViewSites={canViewSites}
                            realAgentAvailable={realAgentAvailable}
                            readiness={readinessBySiteId[site.id]}
                            site={site}
                            onDisableRecord={handleDisableSite}
                            onDisableSite={openDisableModal}
                            onFiles={handleViewFiles}
                            onLogs={handleViewLogs}
                            onMarkReady={handleMarkReady}
                            onPlan={handleViewApplyPlan}
                            onPreview={handlePreviewNginxConfig}
                            onReapply={openReapplyModal}
                          />
                        </td>
                      </tr>
                      {expandedSiteId === site.id ? (
                        <tr className="web-site-details-row" key={`${site.id}-details`}>
                          <td colSpan={5}>
                            <SiteDetails site={site} readiness={readinessBySiteId[site.id]} />
                          </td>
                        </tr>
                      ) : null}
                    </Fragment>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
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
            {preflight ? <PreflightPanel preflight={preflight} /> : null}
            {!realAgentAvailable ? (
              <div className="web-apply-warning">
                <strong>Agent not connected</strong>
                <span>{agentControlMessage}</span>
              </div>
            ) : null}
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
              disabled={
                !canManageSites ||
                !realAgentAvailable ||
                !preflight?.ready ||
                applyPhrase !== applyPlan.confirmation_phrase
              }
              onClick={handleApplyNginxConfig}
              title={!realAgentAvailable ? "Requires a connected local Agent" : undefined}
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
                  setPreflight(null);
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
            {preflight ? <PreflightPanel preflight={preflight} /> : null}
            {!realAgentAvailable ? (
              <div className="web-apply-warning">
                <strong>Agent not connected</strong>
                <span>{agentControlMessage}</span>
              </div>
            ) : null}
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
                !canManageSites ||
                !realAgentAvailable ||
                !preflight?.ready ||
                disablePhrase !== disableConfirmationPhrase(disableTarget)
              }
              onClick={handleDisableNginxConfig}
              title={!realAgentAvailable ? "Requires a connected local Agent" : undefined}
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
                  setPreflight(null);
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
            {preflight ? <PreflightPanel preflight={preflight} /> : null}
            {!realAgentAvailable ? (
              <div className="web-apply-warning">
                <strong>Agent not connected</strong>
                <span>{agentControlMessage}</span>
              </div>
            ) : null}
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
              disabled={
                !canManageSites ||
                !realAgentAvailable ||
                !preflight?.ready ||
                reapplyPhrase !== applyConfirmationPhrase(reapplyTarget)
              }
              onClick={handleReapplyNginxConfig}
              title={!realAgentAvailable ? "Requires a connected local Agent" : undefined}
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
                  setPreflight(null);
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

      {logsTarget ? (
        <div className="modal-backdrop" role="presentation">
          <section className="confirm-modal nginx-preview-modal" aria-label="Web site logs">
            <div>
              <span className="eyebrow">Read-only logs</span>
              <h2>{logsTarget.domain}</h2>
            </div>
            <p>
              Recent HostPilot-managed access and error log lines only. No full download, delete,
              truncate, or arbitrary file access is available.
            </p>
            <div className="modal-actions">
              <button
                className="icon-text-button"
                disabled={logsLoading}
                onClick={() => refreshLogs()}
                type="button"
              >
                <RefreshCw size={15} />
                Refresh
              </button>
            </div>
            {logsLoading ? <span className="empty-table-note">Loading logs.</span> : null}
            {logsResult ? (
              <div className="web-logs-grid">
                <LogViewer title="Access log" log={logsResult.access} />
                <LogViewer title="Error log" log={logsResult.error} />
              </div>
            ) : !logsLoading ? (
              <span className="empty-table-note">No log response loaded.</span>
            ) : null}
            {logsResult ? (
              <div className="apply-plan-section">
                <strong>Agent job</strong>
                <code className="path-code">#{logsResult.job_id}</code>
                <code className="path-code">{logsResult.status}</code>
                <code className="path-code">{logsResult.line_limit} lines max</code>
              </div>
            ) : null}
            <div className="modal-actions">
              <button
                className="icon-text-button"
                onClick={() => {
                  setLogsTarget(null);
                  setLogsResult(null);
                }}
                type="button"
              >
                Close
              </button>
            </div>
          </section>
        </div>
      ) : null}

      {filesTarget ? (
        <div className="modal-backdrop" role="presentation">
          <section className="confirm-modal nginx-preview-modal" aria-label="Web site files">
            <div>
              <span className="eyebrow">Read-only files</span>
              <h2>{filesTarget.domain}</h2>
            </div>
            <p>
              Directory metadata under the site root only. No file contents, uploads, edits,
              deletes, permission changes, or shell access are available.
            </p>
            <div className="apply-plan-section">
              <strong>Current path</strong>
              <code className="path-code">{filesResult?.target_path ?? filesTarget.root_path}</code>
            </div>
            <FileBreadcrumb subpath={filesSubpath} onNavigate={navigateFiles} />
            <div className="modal-actions">
              <button
                className="icon-text-button"
                disabled={filesLoading}
                onClick={() => navigateFiles("", 1)}
                type="button"
              >
                <FolderOpen size={15} />
                Root
              </button>
              <button
                className="icon-text-button"
                disabled={filesLoading}
                onClick={() => refreshFiles()}
                type="button"
              >
                <RefreshCw size={15} />
                Refresh
              </button>
            </div>
            {filesError ? <div className="login-error">{filesError}</div> : null}
            {filesLoading ? <span className="empty-table-note">Loading files.</span> : null}
            {filesResult ? (
              <FileBrowserTable
                entries={filesResult.entries}
                status={filesResult.status}
                onOpenDirectory={(entry) => navigateFiles(entry.relative_path)}
              />
            ) : !filesLoading && !filesError ? (
              <span className="empty-table-note">No file listing loaded.</span>
            ) : null}
            {filesResult ? (
              <div className="apply-plan-section">
                <strong>Listing state</strong>
                <code className="path-code">job #{filesResult.job_id}</code>
                <code className="path-code">{filesResult.status}</code>
                <code className="path-code">{filesResult.total_entries} entries</code>
                <code className="path-code">depth {filesResult.max_depth}</code>
              </div>
            ) : null}
            {filesResult ? (
              <div className="modal-actions">
                <button
                  className="icon-text-button"
                  disabled={filesPage <= 1 || filesLoading}
                  onClick={() => navigateFiles(filesSubpath, filesPage - 1)}
                  type="button"
                >
                  Previous
                </button>
                <button
                  className="icon-text-button"
                  disabled={!filesResult.has_next || filesLoading}
                  onClick={() => navigateFiles(filesSubpath, filesPage + 1)}
                  type="button"
                >
                  Next
                </button>
              </div>
            ) : null}
            <div className="modal-actions">
              <button
                className="icon-text-button"
                onClick={() => {
                  setFilesTarget(null);
                  setFilesResult(null);
                  setFilesError(null);
                  setFilesSubpath("");
                  setFilesPage(1);
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

function LogViewer({ title, log }: { title: string; log: WebSiteLogFile }) {
  return (
    <div className="web-log-viewer">
      <div className="apply-plan-section">
        <strong>{title}</strong>
        <code className="path-code">{log.path || "path unavailable"}</code>
      </div>
      {log.missing ? (
        <span className="empty-table-note">Log file does not exist yet.</span>
      ) : log.lines.length === 0 ? (
        <span className="empty-table-note">Log file is empty.</span>
      ) : (
        <pre className="config-preview-block">
          <code>{log.lines.join("\n")}</code>
        </pre>
      )}
    </div>
  );
}

function FileBreadcrumb({
  subpath,
  onNavigate,
}: {
  subpath: string;
  onNavigate: (subpath: string) => void;
}) {
  const parts = subpath ? subpath.split("/") : [];
  return (
    <div className="file-breadcrumb">
      <button className="icon-text-button" onClick={() => onNavigate("")} type="button">
        Root
      </button>
      {parts.map((part, index) => {
        const path = parts.slice(0, index + 1).join("/");
        return (
          <button className="icon-text-button" key={path} onClick={() => onNavigate(path)} type="button">
            {part}
          </button>
        );
      })}
    </div>
  );
}

function FileBrowserTable({
  entries,
  status,
  onOpenDirectory,
}: {
  entries: WebSiteFileEntry[];
  status: string;
  onOpenDirectory: (entry: WebSiteFileEntry) => void;
}) {
  if (entries.length === 0) {
    const message =
      status === "missing_directory"
        ? "Site root directory does not exist yet. Apply/provision the site first."
        : "Directory is empty.";
    return <span className="empty-table-note">{message}</span>;
  }

  return (
    <div className="data-table-wrap">
      <table className="data-table web-files-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Size</th>
            <th>Modified</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => (
            <tr key={entry.relative_path}>
              <td>
                {entry.type === "directory" ? (
                  <button className="icon-text-button" onClick={() => onOpenDirectory(entry)} type="button">
                    <FolderOpen size={15} />
                    {entry.name}
                  </button>
                ) : (
                  <span className="file-entry-name">
                    <File size={15} />
                    {entry.name}
                  </span>
                )}
              </td>
              <td>{entry.type}</td>
              <td>{formatFileSize(entry.size)}</td>
              <td>{formatModifiedTime(entry.modified_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatFileSize(size: number) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function formatModifiedTime(timestamp: number) {
  if (!timestamp) return "Unknown";
  return new Date(timestamp * 1000).toLocaleString();
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

function ReadinessSummary({ readiness }: { readiness?: WebSiteReadiness }) {
  if (!readiness) {
    return <span className="state-pill">Loading</span>;
  }

  const passed = readiness.checks.filter((check) => check.passed).length;
  const total = readiness.checks.length;
  return (
    <div className="web-compact-stack">
      <span className={`state-pill ${readiness.ready ? "state-active" : "state-disabled"}`}>
        {readiness.ready ? "Ready" : "Needs work"}
      </span>
      <span>{passed}/{total} checks</span>
    </div>
  );
}

function SiteStatusSummary({ site }: { site: WebSite }) {
  return (
    <div className="web-compact-stack">
      <span className={`state-pill web-site-status ${site.status}`}>
        {site.status === "config_pending" ? "Config pending" : site.status}
      </span>
      <span className={`workflow-badge ${site.provisioning_status}`}>
        {workflowLabel(site.provisioning_status)}
      </span>
    </div>
  );
}

function AgentStateChip({
  agentStatus,
  realAgentAvailable,
}: {
  agentStatus: AgentStatus | null;
  realAgentAvailable: boolean;
}) {
  if (!agentStatus) {
    return <span className="state-pill">Checking</span>;
  }

  return (
    <div className="web-compact-stack">
      <span className={`state-pill ${realAgentAvailable ? "state-active" : "state-disabled"}`}>
        {agentStatus.status}
      </span>
      <span>{realAgentAvailable ? "Real Agent" : "controlled actions blocked"}</span>
    </div>
  );
}

function SiteDetails({ site, readiness }: { site: WebSite; readiness?: WebSiteReadiness }) {
  return (
    <div className="web-site-details">
      <div className="web-detail-grid">
        <div>
          <span>Root path</span>
          <code className="path-code">{site.root_path}</code>
        </div>
        <div>
          <span>PHP runtime</span>
          <code className="path-code">{site.php_runtime || "none"}</code>
        </div>
        <div>
          <span>SSL</span>
          <code className="path-code">{site.ssl_enabled ? "flagged only" : "off"}</code>
        </div>
        <div>
          <span>Updated</span>
          <code className="path-code">{formatModifiedTime(Date.parse(site.updated_at) / 1000)}</code>
        </div>
      </div>
      <div className="web-detail-readiness">
        <strong>Readiness checks</strong>
        <ReadinessChecklist readiness={readiness} />
      </div>
    </div>
  );
}

function SiteActionsMenu({
  canManageSites,
  canViewSites,
  realAgentAvailable,
  readiness,
  site,
  onDisableRecord,
  onDisableSite,
  onFiles,
  onLogs,
  onMarkReady,
  onPlan,
  onPreview,
  onReapply,
}: {
  canManageSites: boolean;
  canViewSites: boolean;
  realAgentAvailable: boolean;
  readiness?: WebSiteReadiness;
  site: WebSite;
  onDisableRecord: (siteId: number) => void;
  onDisableSite: (site: WebSite) => void;
  onFiles: (site: WebSite) => void;
  onLogs: (site: WebSite) => void;
  onMarkReady: (siteId: number) => void;
  onPlan: (siteId: number) => void;
  onPreview: (siteId: number) => void;
  onReapply: (site: WebSite) => void;
}) {
  return (
    <details className="web-actions-menu">
      <summary>
        <MoreHorizontal size={16} />
        Actions
      </summary>
      <div className="web-actions-panel">
        <div className="web-actions-group">
          <span>Files / Logs</span>
          <button className="icon-text-button web-files-action" disabled={!canViewSites} onClick={() => onFiles(site)} type="button">
            <FolderOpen size={15} />
            Files
          </button>
          <button className="icon-text-button" disabled={!canViewSites} onClick={() => onLogs(site)} type="button">
            <ScrollText size={15} />
            Logs
          </button>
        </div>
        <div className="web-actions-group">
          <span>Nginx</span>
          <button className="icon-text-button" disabled={!canViewSites} onClick={() => onPreview(site.id)} type="button">
            <FileCode2 size={15} />
            Preview
          </button>
          <button
            className="icon-text-button"
            disabled={!canManageSites || !readiness?.ready}
            onClick={() => onMarkReady(site.id)}
            type="button"
          >
            <ShieldCheck size={15} />
            Mark Ready
          </button>
          <button
            className="icon-text-button"
            disabled={!canViewSites || site.provisioning_status !== "ready_to_apply"}
            onClick={() => onPlan(site.id)}
            type="button"
          >
            <FileText size={15} />
            Plan / Dry-run / Apply
          </button>
        </div>
        <div className="web-actions-group web-actions-danger">
          <span>Lifecycle</span>
          <button
            className="icon-text-button state-disabled"
            disabled={!canManageSites || site.status === "disabled"}
            onClick={() => onDisableRecord(site.id)}
            type="button"
          >
            <Lock size={15} />
            Disable record
          </button>
          <button
            className="icon-text-button state-disabled"
            disabled={!canManageSites || site.status !== "applied" || !realAgentAvailable}
            onClick={() => onDisableSite(site)}
            title={!realAgentAvailable ? "Requires a connected local Agent" : undefined}
            type="button"
          >
            <Lock size={15} />
            Disable site
          </button>
          <button
            className="icon-text-button"
            disabled={!canManageSites || !["disabled", "error"].includes(site.status) || !realAgentAvailable}
            onClick={() => onReapply(site)}
            title={!realAgentAvailable ? "Requires a connected local Agent" : undefined}
            type="button"
          >
            <ShieldCheck size={15} />
            Re-Apply
          </button>
        </div>
      </div>
    </details>
  );
}

function PreflightPanel({ preflight }: { preflight: WebSitePreflight }) {
  return (
    <div className="apply-plan-section">
      <strong>Web Agent preflight</strong>
      <span className={`state-pill ${preflight.ready ? "state-active" : "state-disabled"}`}>
        {preflight.ready ? "Passed" : "Blocked"}
      </span>
      <code className="path-code">
        Agent {preflight.agent_status} / {preflight.agent_mode}
      </code>
      <code className="path-code">Webroot base: {preflight.allowed_web_base_path}</code>
      <code className="path-code">Nginx config base: {preflight.nginx_config_base_path}</code>
      <div className="readiness-list">
        {preflight.checks.map((check) => (
          <span
            className={`readiness-check ${check.passed ? "passed" : "failed"}`}
            key={check.slug}
            title={check.detail}
          >
            {check.label}
          </span>
        ))}
      </div>
      {!preflight.ready ? (
        <span className="empty-table-note">
          Controlled Apply, Disable, and Re-Apply are blocked until preflight passes.
        </span>
      ) : null}
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

function siteSummaryLabel(site: WebSite) {
  if (site.status === "applied") return "Nginx config applied";
  if (site.status === "disabled") return "Nginx config disabled";
  if (site.status === "error") return "Needs review";
  if (site.provisioning_status === "ready_to_apply") return "Ready for Nginx apply";
  if (site.provisioning_status === "config_previewed") return "Nginx preview generated";
  return "Config pending";
}

function fallbackSections(): WebSectionStatus[] {
  return [
    {
      slug: "sites",
      name: "Sites",
      status: "available",
      description: "Create site records and open Files, Logs, and Nginx workflows from each site row.",
      action_label: "Create or select a site record",
      action_available: true,
    },
    {
      slug: "nginx",
      name: "Nginx",
      status: "available",
      description: "Preview, plan, dry-run, apply, disable, and re-apply controlled HostPilot configs.",
      action_label: "Use Nginx actions from a site row",
      action_available: true,
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
      status: "available",
      description: "Read-only recent access and error log tails are available per site.",
      action_label: "Open logs from a site row",
      action_available: true,
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

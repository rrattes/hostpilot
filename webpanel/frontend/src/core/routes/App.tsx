import { useEffect, useState } from "react";

import { getAgentStatus, type AgentStatus } from "../api/agent";
import { listModules, updateModuleState } from "../api/modules";
import {
  listNotifications,
  markNotificationRead,
  type NotificationItem,
} from "../api/notifications";
import { getCoreStatus, type CoreHealthStatus } from "../api/status";
import { AuthProvider, useAuth } from "../auth/AuthProvider";
import { AppLayout } from "../layout/AppLayout";
import type { ModuleDefinition, ModuleState } from "../modules/moduleCatalog";
import { DashboardPage } from "../../pages/DashboardPage";
import { AgentPage } from "../../pages/AgentPage";
import { AuditLogPage } from "../../pages/AuditLogPage";
import { JobsPage } from "../../pages/JobsPage";
import { LoginPage } from "../../pages/LoginPage";
import { NotificationsPage } from "../../pages/NotificationsPage";
import { ServerPage } from "../../pages/ServerPage";
import { SettingsPage } from "../../pages/SettingsPage";

export function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
}

function AppRoutes() {
  const { currentUser, hasPermission, isAuthenticated, isLoading, login, logout, token } = useAuth();
  const [path, setPath] = useState(window.location.pathname);
  const [agentStatus, setAgentStatus] = useState<AgentStatus | null>(null);
  const [healthStatus, setHealthStatus] = useState<CoreHealthStatus | null>(null);
  const [modules, setModules] = useState<ModuleDefinition[]>([]);
  const [moduleError, setModuleError] = useState<string | null>(null);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadNotifications, setUnreadNotifications] = useState(0);
  const isLoginRoute = path === "/login";

  function navigate(nextPath: string) {
    window.history.pushState(null, "", nextPath);
    setPath(nextPath);
  }

  useEffect(() => {
    if (!isLoading && !isAuthenticated && !isLoginRoute) {
      window.history.replaceState(null, "", "/login");
      setPath("/login");
    }
    if (!isLoading && isAuthenticated && isLoginRoute) {
      window.history.replaceState(null, "", "/");
      setPath("/");
    }
  }, [isAuthenticated, isLoading, isLoginRoute]);

  useEffect(() => {
    if (!token || !hasPermission("modules.view")) {
      setModules([]);
      return;
    }

    listModules(token)
      .then((response) => {
        setModules(response);
        setModuleError(null);
      })
      .catch(() => setModuleError("Unable to load module registry."));
  }, [hasPermission, token]);

  async function loadNotifications() {
    if (!token || !hasPermission("notifications.view")) {
      setNotifications([]);
      setUnreadNotifications(0);
      return;
    }

    try {
      const response = await listNotifications(token, 10);
      setNotifications(response.items);
      setUnreadNotifications(response.unread_count);
    } catch {
      setNotifications([]);
      setUnreadNotifications(0);
    }
  }

  useEffect(() => {
    void loadNotifications();
  }, [hasPermission, token]);

  useEffect(() => {
    if (!token || !hasPermission("core.view")) {
      setHealthStatus(null);
      return;
    }

    getCoreStatus(token)
      .then((response) => setHealthStatus(response))
      .catch(() => setHealthStatus(null));
  }, [hasPermission, token, modules]);

  useEffect(() => {
    if (!token || !hasPermission("agent.view")) {
      setAgentStatus(null);
      return;
    }

    getAgentStatus(token)
      .then((response) => setAgentStatus(response))
      .catch(() => setAgentStatus(null));
  }, [hasPermission, token]);

  useEffect(() => {
    function handlePopState() {
      setPath(window.location.pathname);
    }

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  if (isLoading) {
    return (
      <main className="loading-screen">
        <div className="loading-panel">
          <span className="eyebrow">HostPilot</span>
          <strong>Loading session</strong>
        </div>
      </main>
    );
  }

  if (!currentUser) {
    return (
      <LoginPage
        onLogin={async (email, password) => {
          await login(email, password);
          window.history.replaceState(null, "", "/");
          setPath("/");
        }}
      />
    );
  }

  return (
    <AppLayout
      currentPath={path}
      currentUser={currentUser}
      hasPermission={hasPermission}
      modules={modules}
      notifications={notifications}
      onLogout={() => {
        logout();
        window.history.replaceState(null, "", "/login");
        setPath("/login");
      }}
      onNavigate={navigate}
      onNotificationRead={async (id) => {
        if (!token || !hasPermission("notifications.manage_own")) return;
        await markNotificationRead(token, id);
        await loadNotifications();
      }}
      onNotificationsOpen={() => navigate("/notifications")}
      unreadNotifications={unreadNotifications}
    >
      {moduleError ? <div className="login-error">{moduleError}</div> : null}
      {renderProtectedPage(path, hasPermission, agentStatus, healthStatus, modules, async (slug, state) => {
        if (!token || !hasPermission("modules.manage")) {
          return;
        }

        try {
          const updated = await updateModuleState(token, slug, state);
          setModules((current) =>
            current.map((module) => (module.slug === updated.slug ? updated : module)),
          );
          setModuleError(null);
        } catch {
          setModuleError("Unable to update module state.");
        }
      })}
    </AppLayout>
  );
}

function renderProtectedPage(
  path: string,
  hasPermission: (permission: string) => boolean,
  agentStatus: AgentStatus | null,
  healthStatus: CoreHealthStatus | null,
  modules: ModuleDefinition[],
  onModuleStateChange: (slug: string, state: ModuleState) => void,
) {
  if (path === "/agent") {
    return hasPermission("agent.view") ? (
      <AgentPage canExecuteMock={hasPermission("agent.execute_mock")} />
    ) : (
      <DashboardPage
        agentStatus={agentStatus}
        canManageModules={hasPermission("modules.manage")}
        healthStatus={healthStatus}
        modules={modules}
        onModuleStateChange={onModuleStateChange}
      />
    );
  }
  if (path === "/notifications") {
    return hasPermission("notifications.view") ? (
      <NotificationsPage />
    ) : (
      <DashboardPage
        agentStatus={agentStatus}
        canManageModules={hasPermission("modules.manage")}
        healthStatus={healthStatus}
        modules={modules}
        onModuleStateChange={onModuleStateChange}
      />
    );
  }
  if (path === "/server") {
    return hasPermission("core.view") ? (
      <ServerPage canEdit={hasPermission("settings.edit")} />
    ) : (
      <DashboardPage
        agentStatus={agentStatus}
        canManageModules={hasPermission("modules.manage")}
        healthStatus={healthStatus}
        modules={modules}
        onModuleStateChange={onModuleStateChange}
      />
    );
  }
  if (path === "/settings") {
    return hasPermission("settings.view") ? (
      <SettingsPage canEdit={hasPermission("settings.edit")} />
    ) : (
      <DashboardPage
        agentStatus={agentStatus}
        canManageModules={hasPermission("modules.manage")}
        healthStatus={healthStatus}
        modules={modules}
        onModuleStateChange={onModuleStateChange}
      />
    );
  }
  if (path === "/audit") {
    return hasPermission("audit.view") ? (
      <AuditLogPage />
    ) : (
      <DashboardPage
        agentStatus={agentStatus}
        canManageModules={hasPermission("modules.manage")}
        healthStatus={healthStatus}
        modules={modules}
        onModuleStateChange={onModuleStateChange}
      />
    );
  }
  if (path === "/jobs") {
    return hasPermission("jobs.view") ? (
      <JobsPage />
    ) : (
      <DashboardPage
        agentStatus={agentStatus}
        canManageModules={hasPermission("modules.manage")}
        healthStatus={healthStatus}
        modules={modules}
        onModuleStateChange={onModuleStateChange}
      />
    );
  }
  return (
    <DashboardPage
      agentStatus={agentStatus}
      canManageModules={hasPermission("modules.manage")}
      healthStatus={healthStatus}
      modules={modules}
      onModuleStateChange={onModuleStateChange}
    />
  );
}

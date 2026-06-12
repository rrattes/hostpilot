import {
  Activity,
  Archive,
  Bell,
  Boxes,
  ClipboardList,
  CircleHelp,
  ChevronRight,
  Globe2,
  LayoutDashboard,
  LogOut,
  PlayCircle,
  Server,
  RadioTower,
  SlidersHorizontal,
  ShieldCheck,
  Sparkles,
  Wrench,
  UserCircle,
  Users,
} from "lucide-react";
import type { ReactNode } from "react";

import type { CurrentUser } from "../auth/types";
import type { NotificationItem } from "../api/notifications";
import type { ModuleDefinition } from "../modules/moduleCatalog";

interface AppLayoutProps {
  children: ReactNode;
  currentUser: CurrentUser;
  currentPath: string;
  hasPermission: (permission: string) => boolean;
  modules: ModuleDefinition[];
  notifications: NotificationItem[];
  unreadNotifications: number;
  onNavigate: (path: string) => void;
  onLogout: () => void;
  onNotificationRead: (id: number) => void;
  onNotificationsOpen: () => void;
}

export function AppLayout({
  children,
  currentUser,
  currentPath,
  hasPermission,
  modules,
  notifications,
  unreadNotifications,
  onNavigate,
  onLogout,
  onNotificationRead,
  onNotificationsOpen,
}: AppLayoutProps) {
  const infrastructurePages = [
    { label: "Server", path: "/server", icon: Server, permission: "core.view" },
    { label: "Agent", path: "/agent", icon: RadioTower, permission: "agent.view" },
  ];
  const operationsPages = [
    { label: "Notifications", path: "/notifications", icon: Bell, permission: "notifications.view" },
    { label: "Audit Log", path: "/audit", icon: ShieldCheck, permission: "audit.view" },
    { label: "Jobs", path: "/jobs", icon: ClipboardList, permission: "jobs.view" },
  ];
  const settingsPage = { label: "Settings", path: "/settings", icon: SlidersHorizontal, permission: "settings.view" };
  const usersPage = { label: "Users", path: "/users", icon: Users, permission: "core.admin" };
  const rolesPage = { label: "Roles", path: "/roles", icon: ShieldCheck, permission: "core.admin" };
  const backupsPage = { label: "Backups", path: "/backups", icon: Archive, permission: "core.backup.view" };
  const webModule = modules.find((module) => module.slug === "web");
  const webPage = {
    label: "Web",
    path: "/web",
    icon: Globe2,
    permission: "web.view",
    visible: webModule !== undefined && webModule.state !== "locked",
  };
  const settingsPages = [usersPage, rolesPage, backupsPage, settingsPage];
  const modulePages = hasPermission(webPage.permission) && webPage.visible ? [webPage] : [];
  const activeModule = modules.find((module) => module.slug === "core") ?? modules.find((module) => module.enabled);
  const pageTitle = currentPath === "/" ? "Overview" : pageTitleForPath(currentPath);
  const pageSubtitle =
    currentPath === "/"
      ? "Real-time overview of your HostPilot environment."
      : "HostPilot controls and operational context.";
  const renderNavItem = (page: NavPage, variant: "module" | "utility" = "module") => {
    const Icon = page.icon;
    return (
      <button
        className={`${variant === "module" ? "module-nav-item" : "utility-nav-item"} ${
          currentPath === page.path ? "active" : ""
        }`}
        key={page.path}
        onClick={() => onNavigate(page.path)}
        type="button"
      >
        <Icon size={14} />
        <span>{page.label}</span>
      </button>
    );
  };

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Module navigation">
        <div className="brand">
          <Server size={24} />
          <div>
            <strong>HostPilot</strong>
            <span>Core Console</span>
          </div>
        </div>

        <nav className="module-nav" aria-label="Primary navigation">
          {renderNavItem({ label: "Overview", path: "/", icon: LayoutDashboard, permission: "core.view" })}
        </nav>

        <SidebarGroup
          defaultOpen={["/server", "/agent"].includes(currentPath)}
          icon={<Server size={14} />}
          label="Infrastructure"
        >
          {infrastructurePages.filter((page) => hasPermission(page.permission)).map((page) => renderNavItem(page))}
        </SidebarGroup>

        <SidebarGroup
          defaultOpen={["/notifications", "/audit", "/jobs"].includes(currentPath)}
          icon={<Activity size={14} />}
          label="Operations"
        >
          {operationsPages.filter((page) => hasPermission(page.permission)).map((page) => renderNavItem(page))}
        </SidebarGroup>

        {modulePages.length > 0 ? (
          <SidebarGroup defaultOpen={currentPath === "/web"} icon={<Boxes size={14} />} label="Modules">
            {modulePages.map((page) => renderNavItem(page))}
          </SidebarGroup>
        ) : null}

        <SidebarGroup
          defaultOpen={["/users", "/roles", "/backups", "/settings"].includes(currentPath)}
          icon={<Wrench size={14} />}
          label="Settings"
        >
          {settingsPages
            .filter((page) => hasPermission(page.permission))
            .map((page) => renderNavItem(page, "utility"))}
        </SidebarGroup>

        <div className="sidebar-spacer" />

        <div className="quick-actions" aria-label="Quick Actions">
          <span className="sidebar-section-label">Quick Actions</span>
          {hasPermission("audit.view") ? (
            <button className="quick-action-button" onClick={() => onNavigate("/audit")} type="button">
              <ShieldCheck size={14} />
              Run Audit
            </button>
          ) : null}
          {hasPermission("web.view") && webPage.visible ? (
            <button className="quick-action-button" onClick={() => onNavigate("/web")} type="button">
              <Globe2 size={14} />
              View Logs
            </button>
          ) : null}
          {hasPermission("core.backup.view") ? (
            <button className="quick-action-button" onClick={() => onNavigate("/backups")} type="button">
              <Archive size={14} />
              Create Backup
            </button>
          ) : null}
          {hasPermission("jobs.view") ? (
            <button className="quick-action-button" onClick={() => onNavigate("/jobs")} type="button">
              <PlayCircle size={14} />
              New Job
            </button>
          ) : null}
        </div>

        <div className="sidebar-footer">
          <div className="module-context" aria-label="Active platform module">
            <div>
              <strong>{activeModule?.name ?? "Core"}</strong>
              <span>{activeModule?.state ?? "enabled"} module</span>
            </div>
            <ShieldCheck size={15} />
          </div>
        </div>
      </aside>

      <div className="main-area">
        <header className="topbar">
          <div>
            <span className="eyebrow">Local server</span>
            <h1>{pageTitle}</h1>
            <p>{pageSubtitle}</p>
          </div>
          <div className="status-strip" aria-label="Core status">
            <span className="status-chip-operational">
              <ShieldCheck size={16} />
              All Systems Operational
            </span>
            <button className="utility-chip" onClick={() => onNavigate("/server")} type="button">
              <Sparkles size={16} />
              Live Checks
            </button>
            <span>
              <Activity size={16} />
              SQLite
            </span>
            <button className="icon-button notification-button" onClick={onNotificationsOpen} type="button" aria-label="Notifications">
              <Bell size={18} />
              {unreadNotifications > 0 ? <span className="badge-dot">{unreadNotifications}</span> : null}
            </button>
            <button className="icon-button" onClick={() => onNavigate("/settings")} type="button" aria-label="Help">
              <CircleHelp size={18} />
            </button>
            <span>
              <UserCircle size={16} />
              {currentUser.display_name}
            </span>
            <div className="notification-popover">
              {notifications.slice(0, 4).map((notification) => (
                <button
                  className={`notification-mini ${notification.status}`}
                  key={notification.id}
                  onClick={() => onNotificationRead(notification.id)}
                  type="button"
                >
                  <strong>{notification.title}</strong>
                  <span>{notification.message}</span>
                </button>
              ))}
              <button className="notification-mini" onClick={onNotificationsOpen} type="button">
                <strong>Open notifications</strong>
                <span>View all Core messages</span>
              </button>
            </div>
            <button className="icon-button" onClick={onLogout} type="button" aria-label="Sign out">
              <LogOut size={18} />
            </button>
          </div>
        </header>

        <main className="content">{children}</main>
      </div>
    </div>
  );
}

interface NavPage {
  label: string;
  path: string;
  icon: typeof LayoutDashboard;
  permission: string;
}

function SidebarGroup({
  children,
  defaultOpen,
  icon,
  label,
}: {
  children: ReactNode;
  defaultOpen: boolean;
  icon: ReactNode;
  label: string;
}) {
  return (
    <details className="sidebar-group" open={defaultOpen}>
      <summary>
        <span className="sidebar-group-label">
          {icon}
          {label}
        </span>
        <ChevronRight className="sidebar-group-indicator" size={14} />
      </summary>
      <div className="sidebar-group-items">{children}</div>
    </details>
  );
}

function pageTitleForPath(path: string) {
  const titles: Record<string, string> = {
    "/server": "Server",
    "/agent": "Agent",
    "/notifications": "Notifications",
    "/audit": "Audit Log",
    "/jobs": "Jobs",
    "/web": "Web",
    "/users": "Users",
    "/roles": "Roles",
    "/backups": "Backups",
    "/settings": "Settings",
  };
  return titles[path] ?? "Overview";
}

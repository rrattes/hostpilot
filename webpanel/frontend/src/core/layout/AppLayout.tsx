import {
  Activity,
  Archive,
  Bell,
  ClipboardList,
  LayoutDashboard,
  LogOut,
  Server,
  RadioTower,
  SlidersHorizontal,
  ShieldCheck,
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
  const corePages = [
    { label: "Dashboard", path: "/", icon: LayoutDashboard, permission: "core.view" },
    { label: "Server", path: "/server", icon: Server, permission: "core.view" },
    { label: "Agent", path: "/agent", icon: RadioTower, permission: "agent.view" },
    { label: "Notifications", path: "/notifications", icon: Bell, permission: "notifications.view" },
    { label: "Audit Log", path: "/audit", icon: ShieldCheck, permission: "audit.view" },
    { label: "Jobs", path: "/jobs", icon: ClipboardList, permission: "jobs.view" },
  ];
  const settingsPage = { label: "Settings", path: "/settings", icon: SlidersHorizontal, permission: "settings.view" };
  const usersPage = { label: "Users", path: "/users", icon: Users, permission: "core.admin" };
  const backupsPage = { label: "Backups", path: "/backups", icon: Archive, permission: "core.backup.view" };
  const activeModule = modules.find((module) => module.slug === "core") ?? modules.find((module) => module.enabled);

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

        <nav className="module-nav" aria-label="Core navigation">
          {corePages
            .filter((page) => hasPermission(page.permission))
            .map((page) => {
              const Icon = page.icon;
              return (
                <button
                  className={`module-nav-item ${currentPath === page.path ? "active" : ""}`}
                  key={page.path}
                  onClick={() => onNavigate(page.path)}
                  type="button"
                >
                  <span>{page.label}</span>
                  <Icon size={15} />
                </button>
              );
            })}
        </nav>

        <div className="sidebar-spacer" />

        <div className="sidebar-footer">
          <span className="sidebar-section-label">Platform context</span>
          <div className="module-context" aria-label="Active platform module">
            <div>
              <strong>{activeModule?.name ?? "Core"}</strong>
              <span>{activeModule?.state ?? "enabled"} module</span>
            </div>
            <ShieldCheck size={15} />
          </div>

          {[usersPage, backupsPage, settingsPage]
            .filter((page) => hasPermission(page.permission))
            .map((page) => {
              const Icon = page.icon;
              return (
                <button
                  className={`utility-nav-item ${currentPath === page.path ? "active" : ""}`}
                  key={page.path}
                  onClick={() => onNavigate(page.path)}
                  type="button"
                >
                  <span>{page.label}</span>
                  <Icon size={15} />
                </button>
              );
            })}
        </div>
      </aside>

      <div className="main-area">
        <header className="topbar">
          <div>
            <span className="eyebrow">Local server</span>
            <h1>Core Platform</h1>
          </div>
          <div className="status-strip" aria-label="Core status">
            <span>
              <ShieldCheck size={16} />
              Mock agent
            </span>
            <span>
              <Activity size={16} />
              SQLite
            </span>
            <span>
              <UserCircle size={16} />
              {currentUser.display_name}
            </span>
            <button className="icon-button notification-button" onClick={onNotificationsOpen} type="button" aria-label="Notifications">
              <Bell size={18} />
              {unreadNotifications > 0 ? <span className="badge-dot">{unreadNotifications}</span> : null}
            </button>
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

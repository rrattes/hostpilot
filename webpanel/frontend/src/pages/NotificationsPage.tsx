import { useEffect, useState } from "react";

import {
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  type NotificationItem,
} from "../core/api/notifications";
import { apiErrorMessage } from "../core/api/client";
import { useAuth } from "../core/auth/AuthProvider";

export function NotificationsPage() {
  const { token } = useAuth();
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    if (!token) return;
    try {
      const response = await listNotifications(token, 50);
      setItems(response.items);
      setUnreadCount(response.unread_count);
      setError(null);
    } catch (loadError) {
      setError(apiErrorMessage(loadError, "Unable to load notifications."));
    }
  }

  useEffect(() => {
    void load();
  }, [token]);

  async function markRead(id: number) {
    if (!token) return;
    try {
      await markNotificationRead(token, id);
      await load();
    } catch (readError) {
      setError(apiErrorMessage(readError, "Unable to mark notification as read."));
    }
  }

  async function markAllRead() {
    if (!token) return;
    try {
      await markAllNotificationsRead(token);
      await load();
    } catch (readError) {
      setError(apiErrorMessage(readError, "Unable to mark notifications as read."));
    }
  }

  return (
    <section className="data-page" aria-label="Notifications">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Core messages</span>
          <h2>Notifications</h2>
        </div>
        <div className="page-actions">
          <span className="count-pill">{unreadCount} unread</span>
          <button className="primary-button compact" onClick={markAllRead} type="button">
            Mark all read
          </button>
        </div>
      </div>
      {error ? <div className="login-error">{error}</div> : null}
      <div className="notification-list">
        {items.map((item) => (
          <article className={`notification-row ${item.status}`} key={item.id}>
            <div>
              <h3>{item.title}</h3>
              <p>{item.message}</p>
              <span>{formatDate(item.created_at)}</span>
            </div>
            {item.status === "unread" ? (
              <button className="icon-text-button" onClick={() => markRead(item.id)} type="button">
                Mark read
              </button>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "short",
    timeStyle: "medium",
  }).format(new Date(value));
}

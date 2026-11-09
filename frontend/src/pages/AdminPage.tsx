import { useCallback, useEffect, useState } from "react";

import { api, errorMessage } from "../api";
import type { Page, Role, User } from "../types";

const PAGE_SIZE = 20;

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ru-RU");
}

export function AdminPage() {
  const [page, setPage] = useState<Page<User> | null>(null);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<number | null>(null);

  const load = useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      setPage(await api.users(PAGE_SIZE, offset));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [offset]);

  useEffect(() => {
    void load();
  }, [load]);

  async function changeRole(user: User, role: Role): Promise<void> {
    setSavingId(user.id);
    setError(null);
    try {
      await api.setRole(user.id, role);
      await load();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSavingId(null);
    }
  }

  const total = page?.total ?? 0;
  const shownFrom = total === 0 ? 0 : offset + 1;
  const shownTo = Math.min(offset + PAGE_SIZE, total);

  return (
    <section className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">Пользователи</h1>
          <p className="page-subtitle">Всего пользователей: {total}</p>
        </div>
      </div>

      {error && <div className="alert error">{error}</div>}

      <div className="card">
        {loading ? (
          <p className="muted">Загрузка…</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Пользователь</th>
                <th>Email</th>
                <th>Роль</th>
                <th>Создан</th>
              </tr>
            </thead>
            <tbody>
              {page?.items.map((user) => (
                <tr key={user.id}>
                  <td>
                    <div className="task-title">{user.name}</div>
                    <div className="task-description">#{user.id}</div>
                  </td>
                  <td>{user.email}</td>
                  <td>
                    <select
                      className="role-select"
                      value={user.role}
                      disabled={savingId === user.id}
                      onChange={(event) => void changeRole(user, event.target.value as Role)}
                    >
                      <option value="USER">USER</option>
                      <option value="ADMIN">ADMIN</option>
                    </select>
                  </td>
                  <td>{formatDate(user.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="pagination">
        <span className="muted">
          {shownFrom}–{shownTo} из {total}
        </span>
        <div className="pagination-buttons">
          <button
            className="button small"
            type="button"
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
          >
            Назад
          </button>
          <button
            className="button small"
            type="button"
            disabled={shownTo >= total}
            onClick={() => setOffset(offset + PAGE_SIZE)}
          >
            Вперёд
          </button>
        </div>
      </div>
    </section>
  );
}

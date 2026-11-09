import type { Page, Role, Task, TaskPayload, TaskQuery, TokenResponse, User } from "./types";

const TOKEN_KEY = "tms_token";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Что-то пошло не так";
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

function formatDetail(detail: unknown): string {
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const entry = item as { loc?: (string | number)[]; msg?: string };
        const field = entry.loc?.filter((part) => part !== "body").join(".");
        return field ? `${field}: ${entry.msg ?? ""}` : String(entry.msg ?? "");
      })
      .join("; ");
  }
  return "Ошибка запроса";
}

function buildQuery(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") {
      search.set(key, String(value));
    }
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }
  const token = getToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(path, { ...init, headers });
  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  const data: unknown = text ? JSON.parse(text) : null;

  if (!response.ok) {
    if (response.status === 401 && token) {
      setToken(null);
      window.dispatchEvent(new Event("tms:unauthorized"));
    }
    const detail = data && typeof data === "object" ? (data as { detail?: unknown }).detail : undefined;
    throw new ApiError(response.status, formatDetail(detail));
  }
  return data as T;
}

export const api = {
  register(email: string, password: string, name: string): Promise<User> {
    return request<User>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, name }),
    });
  },

  login(email: string, password: string): Promise<TokenResponse> {
    return request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  },

  profile(): Promise<User> {
    return request<User>("/auth/profile");
  },

  tasks(query: TaskQuery): Promise<Page<Task>> {
    return request<Page<Task>>(
      `/tasks${buildQuery({
        status: query.status,
        priority: query.priority,
        deadline_from: query.deadline_from,
        deadline_to: query.deadline_to,
        limit: query.limit,
        offset: query.offset,
      })}`,
    );
  },

  createTask(payload: TaskPayload): Promise<Task> {
    return request<Task>("/tasks", { method: "POST", body: JSON.stringify(payload) });
  },

  updateTask(id: number, payload: Partial<TaskPayload>): Promise<Task> {
    return request<Task>(`/tasks/${id}`, { method: "PUT", body: JSON.stringify(payload) });
  },

  deleteTask(id: number): Promise<void> {
    return request<void>(`/tasks/${id}`, { method: "DELETE" });
  },

  users(limit: number, offset: number): Promise<Page<User>> {
    return request<Page<User>>(`/admin/users${buildQuery({ limit, offset })}`);
  },

  setRole(id: number, role: Role): Promise<User> {
    return request<User>(`/admin/users/${id}/role`, {
      method: "PUT",
      body: JSON.stringify({ role }),
    });
  },
};

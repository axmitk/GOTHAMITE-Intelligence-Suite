import { useCallback, useEffect, useState } from "react";

const BASE = "/api/v1/workbench";
let session: Promise<{ csrf: string }> | undefined;

export async function getSession() {
  if (!session) {
    session = fetch(`${BASE}/session`, {
      method: "POST",
      headers: { "X-Gothamite-Client": "workbench" },
      credentials: "same-origin",
    })
      .then(async (r) => {
        if (!r.ok)
          throw new Error(
            "Could not start the local demo session. Check the backend connection.",
          );
        return r.json() as Promise<{ csrf: string }>;
      })
      .catch((error) => {
        session = undefined;
        throw error;
      });
  }
  return session;
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
  retry = true,
): Promise<T> {
  const auth = await getSession();
  const headers = new Headers(options.headers);
  headers.set("X-CSRF-Token", auth.csrf);
  if (options.body) headers.set("Content-Type", "application/json");
  const response = await fetch(`${BASE}${path}`, {
    ...options,
    headers,
    credentials: "same-origin",
  });
  if (response.status === 401 && retry) {
    session = undefined;
    return api<T>(path, options, false);
  }
  if (!response.ok) {
    const error = (await response
      .json()
      .catch(() => ({ detail: `Request failed (${response.status})` }))) as {
      detail?: string;
      errors?: string[];
    };
    throw new Error(
      error.detail ||
        error.errors?.join("; ") ||
        `Request failed (${response.status})`,
    );
  }
  return response.headers.get("content-type")?.includes("application/json")
    ? (response.json() as Promise<T>)
    : (response.text() as Promise<T>);
}

export function useResource<T>(path: string) {
  const [tick, setTick] = useState(0);
  const [state, setState] = useState<{
    path: string;
    data?: T;
    error?: string;
    loading: boolean;
  }>({ path, loading: true });
  const reload = useCallback(() => {
    setState((previous) => ({ ...previous, loading: true }));
    setTick((t) => t + 1);
  }, []);
  const setData = useCallback(
    (data: T) => setState({ path, data, loading: false }),
    [path],
  );
  useEffect(() => {
    const controller = new AbortController();
    api<T>(path, { signal: controller.signal })
      .then((data) => {
        if (!controller.signal.aborted)
          setState({ path, data, loading: false });
      })
      .catch((error) => {
        if (!controller.signal.aborted)
          setState({
            path,
            error: error instanceof Error ? error.message : "Request failed",
            loading: false,
          });
      });
    return () => controller.abort();
  }, [path, tick]);
  return {
    ...(state.path === path
      ? state
      : { loading: true, data: undefined, error: undefined }),
    reload,
    setData,
  };
}

export async function downloadReport(id: string) {
  const content = await api<string>(`/cases/${encodeURIComponent(id)}/report`);
  const url = URL.createObjectURL(
    new Blob([content], { type: "text/markdown;charset=utf-8" }),
  );
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `GOTHAMITE-${id}.md`;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

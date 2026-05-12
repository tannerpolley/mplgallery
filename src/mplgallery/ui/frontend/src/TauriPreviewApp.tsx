import { useEffect, useMemo, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import App from "./App";
import type { AppHost } from "./appHost";
import { mockBootstrap, mockScanResult } from "./tauriMockData";
import { tauriToBrowserPayload } from "./tauriPayload";
import type { TauriBootstrap, TauriScanResult } from "./tauri-types";
import "./tauri-preview.css";

async function loadBootstrap(): Promise<TauriBootstrap> {
  try {
    return await invoke<TauriBootstrap>("get_app_bootstrap");
  } catch {
    return mockBootstrap;
  }
}

async function loadScanResult(rootPath: string): Promise<TauriScanResult> {
  try {
    return await invoke<TauriScanResult>("scan_project", { rootPath });
  } catch {
    return mockScanResult;
  }
}

async function pickProjectRoot(currentRoot: string): Promise<string | null> {
  try {
    return await invoke<string | null>("pick_project_root", { currentRoot });
  } catch {
    const fallback = window.prompt("Project path", currentRoot)?.trim();
    return fallback || null;
  }
}

export default function TauriPreviewApp() {
  const [bootstrap, setBootstrap] = useState<TauriBootstrap | null>(null);
  const [scan, setScan] = useState<TauriScanResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [browseModeOverride, setBrowseModeOverride] = useState<"plot-set-manager" | "image-library" | undefined>(undefined);
  const [baseRoot, setBaseRoot] = useState("");

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    loadBootstrap()
      .then(async (nextBootstrap) => {
        const nextScan = await loadScanResult(nextBootstrap.rootContext.activeRoot);
        if (!mounted) return;
        setBootstrap(nextBootstrap);
        setScan(nextScan);
        setBaseRoot(nextBootstrap.rootContext.activeRoot);
        setLoading(false);
      })
      .catch(() => {
        if (!mounted) return;
        setBootstrap(mockBootstrap);
        setScan(mockScanResult);
        setBaseRoot(mockBootstrap.rootContext.activeRoot);
        setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const payload = useMemo(
    () => (bootstrap && scan ? tauriToBrowserPayload(bootstrap, scan, browseModeOverride) : undefined),
    [bootstrap, scan, browseModeOverride],
  );

  const host = useMemo<AppHost>(
    () => ({
      capabilities: {
        supportsDrafting: false,
        supportsEditing: false,
        supportsBrowseDialog: true,
        supportsRootReset: true,
        supportsInlineUpdateInstall: false,
      },
      openExternal: (url) => window.open(url, "_blank", "noopener,noreferrer"),
      emitEvent: async (event) => {
        if (!bootstrap || !scan) return;
        switch (event.type) {
          case "set_browse_mode":
            setBrowseModeOverride(event.browse_mode);
            return;
          case "refresh_index": {
            const nextScan = await loadScanResult(bootstrap.rootContext.activeRoot);
            setScan(nextScan);
            return;
          }
          case "change_project_root": {
            const rootPath = event.root_path.trim();
            if (!rootPath) return;
            const nextScan = await loadScanResult(rootPath);
            setScan(nextScan);
            setBootstrap((current) => {
              if (!current) return current;
              const recentRoots = current.userSettings.rememberRecentProjects
                ? [rootPath, ...current.rootContext.recentRoots.filter((root) => root !== rootPath)].slice(0, 8)
                : current.rootContext.recentRoots;
              return {
                ...current,
                rootContext: {
                  ...current.rootContext,
                  activeRoot: rootPath,
                  recentRoots,
                  error: null,
                },
              };
            });
            return;
          }
          case "browse_project_root": {
            const rootPath = await pickProjectRoot(bootstrap.rootContext.activeRoot);
            if (!rootPath) return;
            const nextScan = await loadScanResult(rootPath);
            setScan(nextScan);
            setBootstrap((current) => {
              if (!current) return current;
              const recentRoots = current.userSettings.rememberRecentProjects
                ? [rootPath, ...current.rootContext.recentRoots.filter((root) => root !== rootPath)].slice(0, 8)
                : current.rootContext.recentRoots;
              return {
                ...current,
                rootContext: {
                  ...current.rootContext,
                  activeRoot: rootPath,
                  recentRoots,
                  error: null,
                },
              };
            });
            return;
          }
          case "reset_project_root": {
            if (!baseRoot) return;
            const nextScan = await loadScanResult(baseRoot);
            setScan(nextScan);
            setBootstrap((current) => {
              if (!current) return current;
              return {
                ...current,
                rootContext: {
                  ...current.rootContext,
                  activeRoot: baseRoot,
                  error: null,
                },
              };
            });
            return;
          }
          case "forget_recent_root":
            setBootstrap((current) => {
              if (!current) return current;
              const recentRoots = current.rootContext.recentRoots.filter((root) => root !== event.root_path);
              const activeRoot = current.rootContext.activeRoot === event.root_path ? "" : current.rootContext.activeRoot;
              return {
                ...current,
                rootContext: {
                  ...current.rootContext,
                  activeRoot,
                  recentRoots,
                },
              };
            });
            return;
          case "clear_recent_roots":
            setBootstrap((current) =>
              current
                ? {
                  ...current,
                  rootContext: {
                    ...current.rootContext,
                    recentRoots: [],
                  },
                }
                : current);
            return;
          case "set_user_setting":
            setBootstrap((current) =>
              current
                ? {
                  ...current,
                  userSettings: {
                    ...current.userSettings,
                    rememberRecentProjects:
                      event.setting_key === "remember_recent_projects"
                        ? event.setting_value
                        : current.userSettings.rememberRecentProjects,
                    restoreLastProjectOnStartup:
                      event.setting_key === "restore_last_project_on_startup"
                        ? event.setting_value
                        : current.userSettings.restoreLastProjectOnStartup,
                  },
                }
                : current);
            return;
          case "install_update":
            window.open(event.download_url, "_blank", "noopener,noreferrer");
            return;
          default:
            return;
        }
      },
    }),
    [baseRoot, bootstrap, scan],
  );

  if (loading || !bootstrap || !scan || !payload) {
    return <div className="mg-tauri-loading">Loading Tauri desktop preview...</div>;
  }

  return <App payload={payload} host={host} />;
}

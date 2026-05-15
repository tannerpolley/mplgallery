import { useEffect, useMemo, useRef, useState } from "react";
import App from "./App";
import { defaultHostCapabilities, type AppHost } from "./appHost";
import type { BrowserPayload, ComponentEvent } from "./types";

async function postBrowserPreviewEvent(event: ComponentEvent, currentRoot: string): Promise<BrowserPayload> {
  const response = await fetch("/__mplgallery__/event", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      type: event.type,
      currentRoot,
      rootPath: "root_path" in event ? event.root_path : undefined,
      settingKey: "setting_key" in event ? event.setting_key : undefined,
      settingValue: "setting_value" in event ? event.setting_value : undefined,
    }),
  });
  if (!response.ok) {
    throw new Error(`Browser preview request failed: ${response.status}`);
  }
  return response.json() as Promise<BrowserPayload>;
}

function browserPreviewMessage(event: ComponentEvent): string | null {
  switch (event.type) {
    case "change_project_root":
    case "reset_project_root":
      return "Loading project...";
    case "refresh_index":
      return "Refreshing...";
    case "forget_recent_root":
      return "Updating recent projects...";
    case "set_user_setting":
    case "clear_recent_roots":
      return "Saving settings...";
    default:
      return null;
  }
}

export default function BrowserPreviewApp({ initialPayload }: { initialPayload: BrowserPayload }) {
  const [payload, setPayload] = useState<BrowserPayload>(initialPayload);
  const [pendingMessage, setPendingMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const currentRoot = payload.rootContext?.activeRoot ?? "";
  const currentRootRef = useRef(currentRoot);

  useEffect(() => {
    currentRootRef.current = currentRoot;
  }, [currentRoot]);

  const host = useMemo<AppHost>(
    () => ({
      emitEvent: async (event) => {
        switch (event.type) {
          case "refresh_index":
          case "change_project_root":
          case "browse_project_root":
          case "reset_project_root":
          case "forget_recent_root":
          case "set_user_setting":
          case "clear_recent_roots": {
            setErrorMessage(null);
            setPendingMessage(browserPreviewMessage(event));
            try {
              const nextPayload = await postBrowserPreviewEvent(event, currentRootRef.current);
              setPayload(nextPayload);
            } catch (error) {
              setErrorMessage(error instanceof Error ? error.message : "Browser preview request failed.");
            } finally {
              setPendingMessage(null);
            }
            return;
          }
          case "install_update":
            if (event.download_url) window.open(event.download_url, "_blank", "noopener,noreferrer");
            return;
          default:
            return;
        }
      },
      openExternal: (url) => window.open(url, "_blank", "noopener,noreferrer"),
      capabilities: {
        ...defaultHostCapabilities,
        supportsBrowseDialog: false,
        supportsRootReset: true,
      },
    }),
    [currentRoot],
  );

  return (
    <div className="mg-browser-preview-shell">
      <App payload={payload} host={host} />
      {pendingMessage ? (
        <div className="mg-browser-preview-status" role="status" aria-live="polite">
          {pendingMessage}
        </div>
      ) : null}
      {errorMessage ? (
        <div className="mg-browser-preview-error" role="alert">
          {errorMessage}
        </div>
      ) : null}
    </div>
  );
}

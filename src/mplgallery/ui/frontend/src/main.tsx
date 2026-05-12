import App from "./App";
import { defaultHostCapabilities, type AppHost } from "./appHost";
import ReactDOM from "react-dom/client";
import TauriPreviewApp from "./TauriPreviewApp";
import "./App.css";

declare global {
  interface Window {
    __MPLGALLERY_BROWSER_PAYLOAD__?: Parameters<typeof App>[0]["payload"];
  }
}

const browserPreviewHost: AppHost = {
  emitEvent: () => undefined,
  openExternal: (url) => window.open(url, "_blank", "noopener,noreferrer"),
  capabilities: {
    ...defaultHostCapabilities,
    supportsBrowseDialog: false,
    supportsRootReset: false,
  },
};

const payload = window.__MPLGALLERY_BROWSER_PAYLOAD__;

ReactDOM.createRoot(document.getElementById("root")!).render(
  payload ? <App payload={payload} host={browserPreviewHost} /> : <TauriPreviewApp />,
);

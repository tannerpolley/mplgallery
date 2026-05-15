import BrowserPreviewApp from "./BrowserPreviewApp";
import ReactDOM from "react-dom/client";
import TauriPreviewApp from "./TauriPreviewApp";
import type { BrowserPayload } from "./types";
import "./App.css";

declare global {
  interface Window {
    __MPLGALLERY_BROWSER_PAYLOAD__?: BrowserPayload;
  }
}

const payload = window.__MPLGALLERY_BROWSER_PAYLOAD__;

ReactDOM.createRoot(document.getElementById("root")!).render(
  payload ? <BrowserPreviewApp initialPayload={payload} /> : <TauriPreviewApp />,
);

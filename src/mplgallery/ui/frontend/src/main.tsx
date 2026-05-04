import React from "react";
import ReactDOM from "react-dom/client";
import { Streamlit } from "streamlit-component-lib";
import App from "./App";
import type { BrowserPayload } from "./types";

type StreamlitRenderEvent = Event & {
  detail?: {
    args?: {
      payload?: BrowserPayload;
    };
  };
};

function Root() {
  const [payload, setPayload] = React.useState<BrowserPayload | undefined>();

  React.useEffect(() => {
    const reportFrameHeight = () => {
      const height = Math.max(
        document.body.scrollHeight,
        document.documentElement.scrollHeight,
        document.body.offsetHeight,
        document.documentElement.offsetHeight,
      );
      Streamlit.setFrameHeight(height);
    };

    const onRender = (event: Event) => {
      setPayload((event as StreamlitRenderEvent).detail?.args?.payload);
      window.requestAnimationFrame(reportFrameHeight);
    };

    Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, onRender);
    Streamlit.setComponentReady();
    window.requestAnimationFrame(reportFrameHeight);

    const resizeObserver = new ResizeObserver(reportFrameHeight);
    resizeObserver.observe(document.body);

    return () => {
      resizeObserver.disconnect();
      Streamlit.events.removeEventListener(Streamlit.RENDER_EVENT, onRender);
    };
  }, []);

  return <App payload={payload} />;
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>,
);

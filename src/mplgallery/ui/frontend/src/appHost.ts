import type { ComponentEvent } from "./types";

export type AppHostCapabilities = {
  supportsDrafting: boolean;
  supportsEditing: boolean;
  supportsBrowseDialog: boolean;
  supportsRootReset: boolean;
  supportsInlineUpdateInstall: boolean;
};

export type AppHost = {
  emitEvent: (event: ComponentEvent) => void | Promise<void>;
  openExternal: (url: string) => void;
  capabilities?: Partial<AppHostCapabilities>;
};

export const defaultHostCapabilities: AppHostCapabilities = {
  supportsDrafting: false,
  supportsEditing: false,
  supportsBrowseDialog: true,
  supportsRootReset: true,
  supportsInlineUpdateInstall: false,
};

export const noopHost: AppHost = {
  emitEvent: () => undefined,
  openExternal: (url) => window.open(url, "_blank", "noopener,noreferrer"),
  capabilities: defaultHostCapabilities,
};

"""Streamlit application entry point for the local artifact browser."""

from __future__ import annotations

import argparse
import base64
import html
import json
from pathlib import Path
from textwrap import dedent

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from mplgallery.core.associations import build_plot_records
from mplgallery.core.manifest import load_manifest
from mplgallery.core.models import PlotRecord
from mplgallery.core.renderer import render_cached_plot
from mplgallery.core.scanner import scan_project


def main() -> None:
    args = _parse_args()
    project_root = args.project_root.expanduser().resolve()
    st.set_page_config(page_title="MPLGallery", layout="wide", initial_sidebar_state="collapsed")
    st.markdown(
        """
        <style>
        .stApp, [data-testid="stAppViewContainer"], .main {
            background: #f7f8fa;
            color: #17202f;
        }
        header[data-testid="stHeader"] {
            background: transparent;
        }
        .block-container {
            padding-top: 2.5rem;
            max-width: 1280px;
        }
        h1, p, span, label {
            color: #17202f;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.title("MPLGallery")
    st.caption(str(project_root))

    try:
        scan = scan_project(project_root)
        records = [
            render_cached_plot(project_root, record)
            for record in build_plot_records(scan, manifest=load_manifest(project_root))
        ]
    except Exception as exc:  # pragma: no cover - Streamlit display path
        st.error(f"Unable to scan project: {exc}")
        return

    components.html(_render_browser(records), height=900, scrolling=True)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path("."))
    return parser.parse_args()


def _render_browser(records: list[PlotRecord]) -> str:
    payload = [_record_payload(record) for record in records]
    return dedent(
        f"""
        <!doctype html>
        <html lang="en">
        <head>
          <meta charset="utf-8" />
          <style>
            :root {{
              color-scheme: light;
              --bg: #f7f8fa;
              --panel: #ffffff;
              --line: #d9dee7;
              --line-strong: #b7c0ce;
              --ink: #17202f;
              --muted: #5e6a7d;
              --accent: #256f8f;
              --good: #1f7a4d;
              --warn: #9a5b12;
              --bad: #a03636;
            }}

            * {{ box-sizing: border-box; }}
            body {{
              margin: 0;
              background: var(--bg);
              color: var(--ink);
              font-family: "Aptos", "Segoe UI", sans-serif;
              font-size: 14px;
            }}
            .shell {{
              display: grid;
              grid-template-columns: 300px 1fr;
              min-height: 860px;
              border: 1px solid var(--line);
              background: var(--panel);
            }}
            aside {{
              border-right: 1px solid var(--line);
              background: #fbfcfd;
              padding: 14px;
              overflow: auto;
            }}
            main {{
              min-width: 0;
              padding: 14px 16px 24px;
              overflow: auto;
            }}
            .toolbar, .tree-actions {{
              display: flex;
              align-items: center;
              gap: 8px;
              flex-wrap: wrap;
            }}
            .toolbar {{
              justify-content: space-between;
              margin-bottom: 12px;
              border-bottom: 1px solid var(--line);
              padding-bottom: 10px;
            }}
            .title {{
              font-size: 13px;
              font-weight: 700;
              text-transform: uppercase;
              letter-spacing: 0;
              color: var(--muted);
            }}
            input[type="search"] {{
              width: 100%;
              margin: 10px 0;
              padding: 8px 10px;
              border: 1px solid var(--line-strong);
              border-radius: 4px;
              font: inherit;
            }}
            button {{
              border: 1px solid var(--line-strong);
              background: #fff;
              border-radius: 4px;
              padding: 5px 8px;
              color: var(--ink);
              font: inherit;
              font-size: 12px;
              cursor: pointer;
            }}
            button:hover {{ border-color: var(--accent); color: var(--accent); }}
            .tree {{ margin-top: 12px; }}
            .tree-row {{
              display: grid;
              grid-template-columns: 22px 18px 1fr auto;
              align-items: center;
              gap: 4px;
              min-height: 26px;
              border-radius: 3px;
              padding: 1px 2px;
            }}
            .tree-row:hover {{ background: #eef3f7; }}
            .twisty {{
              width: 20px;
              height: 20px;
              padding: 0;
              border: 0;
              background: transparent;
              font-size: 12px;
            }}
            .folder-label {{
              overflow: hidden;
              white-space: nowrap;
              text-overflow: ellipsis;
            }}
            .count {{ color: var(--muted); font-size: 12px; }}
            .children {{ margin-left: 17px; }}
            .grid {{
              display: grid;
              grid-template-columns: repeat(auto-fill, minmax(var(--tile-size), 1fr));
              gap: 12px;
            }}
            .card {{
              border: 1px solid var(--line);
              border-radius: 6px;
              background: #fff;
              overflow: hidden;
              min-width: 0;
            }}
            .thumb {{
              width: 100%;
              height: calc(var(--tile-size) * 0.72);
              object-fit: contain;
              display: block;
              background: #fff;
              border-bottom: 1px solid var(--line);
            }}
            .card-body {{ padding: 8px 9px 9px; }}
            .name {{
              font-weight: 650;
              overflow: hidden;
              white-space: nowrap;
              text-overflow: ellipsis;
            }}
            .meta {{
              display: flex;
              flex-wrap: wrap;
              gap: 5px;
              margin-top: 6px;
            }}
            .badge {{
              border: 1px solid var(--line);
              border-radius: 3px;
              padding: 2px 5px;
              color: var(--muted);
              font-size: 11px;
            }}
            .badge.good {{ color: var(--good); border-color: #9cc9b4; }}
            .badge.warn {{ color: var(--warn); border-color: #d8b56f; }}
            .badge.bad {{ color: var(--bad); border-color: #d8a3a3; }}
            details {{
              margin-top: 7px;
              color: var(--muted);
              font-size: 12px;
            }}
            summary {{ cursor: pointer; }}
            code {{
              display: block;
              white-space: pre-wrap;
              overflow-wrap: anywhere;
              margin-top: 5px;
            }}
            .empty {{
              border: 1px dashed var(--line-strong);
              padding: 36px;
              text-align: center;
              color: var(--muted);
            }}
            @media (max-width: 560px) {{
              .shell {{ grid-template-columns: 1fr; }}
              aside {{ border-right: 0; border-bottom: 1px solid var(--line); max-height: 320px; }}
            }}
          </style>
        </head>
        <body>
          <div class="shell">
            <aside>
              <div class="title">Output tree</div>
              <input id="search" type="search" placeholder="Search plots or CSV files" />
              <div class="tree-actions">
                <button type="button" id="expand">Expand all</button>
                <button type="button" id="collapse">Collapse all</button>
                <button type="button" id="clear">Clear</button>
              </div>
              <div id="tree" class="tree"></div>
            </aside>
            <main>
              <div class="toolbar">
                <div>
                  <strong id="visibleCount">0 plots</strong>
                  <span id="status"></span>
                </div>
                <label>Tile size <input id="tile" type="range" min="170" max="420" value="260" /></label>
              </div>
              <div id="grid" class="grid"></div>
            </main>
          </div>
          <script>
            const records = {json.dumps(payload)};
            const state = {{
              expanded: new Set(["."]),
              selected: new Set(["."]),
              query: "",
              tile: 260,
            }};

            function foldersFor(record) {{
              const parts = record.image_path.split("/");
              const folders = ["."];
              let current = "";
              for (let i = 0; i < parts.length - 1; i += 1) {{
                current = current ? `${{current}}/${{parts[i]}}` : parts[i];
                folders.push(current);
              }}
              return folders;
            }}

            const folderMap = new Map();
            records.forEach((record) => {{
              foldersFor(record).forEach((folder) => {{
                if (!folderMap.has(folder)) folderMap.set(folder, new Set());
                folderMap.get(folder).add(record.id);
              }});
            }});

            function childFolders(parent) {{
              const prefix = parent === "." ? "" : `${{parent}}/`;
              return [...folderMap.keys()]
                .filter((folder) => folder !== parent && folder.startsWith(prefix))
                .filter((folder) => {{
                  const rest = folder.slice(prefix.length);
                  return !rest.includes("/");
                }})
                .sort();
            }}

            function recordMatches(record) {{
              const query = state.query.toLowerCase();
              const textMatch = !query || `${{record.name}} ${{record.image_path}} ${{record.csv_path || ""}}`.toLowerCase().includes(query);
              const selectedMatch = foldersFor(record).some((folder) => state.selected.has(folder));
              return textMatch && selectedMatch;
            }}

            function renderTree() {{
              const tree = document.getElementById("tree");
              tree.innerHTML = "";
              tree.appendChild(renderFolder("."));
            }}

            function renderFolder(folder) {{
              const wrapper = document.createElement("div");
              const row = document.createElement("div");
              row.className = "tree-row";
              const children = childFolders(folder);
              const twisty = document.createElement("button");
              twisty.className = "twisty";
              twisty.type = "button";
              twisty.textContent = children.length ? (state.expanded.has(folder) ? "▾" : "▸") : "";
              twisty.addEventListener("click", () => {{
                if (state.expanded.has(folder)) state.expanded.delete(folder);
                else state.expanded.add(folder);
                render();
              }});

              const checkbox = document.createElement("input");
              checkbox.type = "checkbox";
              checkbox.checked = state.selected.has(folder);
              checkbox.addEventListener("change", () => {{
                if (checkbox.checked) state.selected.add(folder);
                else state.selected.delete(folder);
                renderGrid();
              }});

              const label = document.createElement("div");
              label.className = "folder-label";
              label.title = folder;
              label.textContent = folder === "." ? "All plots" : folder.split("/").at(-1);

              const count = document.createElement("div");
              count.className = "count";
              count.textContent = folderMap.get(folder)?.size ?? 0;

              row.append(twisty, checkbox, label, count);
              wrapper.appendChild(row);

              if (state.expanded.has(folder) && children.length) {{
                const branch = document.createElement("div");
                branch.className = "children";
                children.forEach((child) => branch.appendChild(renderFolder(child)));
                wrapper.appendChild(branch);
              }}
              return wrapper;
            }}

            function renderGrid() {{
              document.documentElement.style.setProperty("--tile-size", `${{state.tile}}px`);
              const grid = document.getElementById("grid");
              const visible = records.filter(recordMatches);
              document.getElementById("visibleCount").textContent = `${{visible.length}} plot${{visible.length === 1 ? "" : "s"}}`;
              document.getElementById("status").textContent = ` of ${{records.length}} indexed`;
              grid.innerHTML = "";
              if (!visible.length) {{
                const empty = document.createElement("div");
                empty.className = "empty";
                empty.textContent = "No plots match the current tree selection and search.";
                grid.appendChild(empty);
                return;
              }}
              visible.forEach((record) => grid.appendChild(renderCard(record)));
            }}

            function renderCard(record) {{
              const card = document.createElement("article");
              card.className = "card";
              const image = document.createElement("img");
              image.className = "thumb";
              image.src = record.image_src;
              image.alt = record.name;

              const body = document.createElement("div");
              body.className = "card-body";
              body.innerHTML = `
                <div class="name" title="${{escapeHtml(record.image_path)}}">${{escapeHtml(record.name)}}</div>
                <div class="meta">
                  <span class="badge">${{record.kind}}</span>
                  <span class="badge ${{record.csv_path ? "good" : "bad"}}">${{record.csv_path ? "CSV matched" : "CSV missing"}}</span>
                  <span class="badge ${{record.confidence === "high" || record.confidence === "exact" ? "good" : "warn"}}">${{record.confidence}}</span>
                </div>
                <details>
                  <summary>details</summary>
                  <code>image: ${{escapeHtml(record.image_path)}}
csv: ${{escapeHtml(record.csv_path || "unmatched")}}
cache: ${{escapeHtml(record.cache_path || "not rendered")}}
reason: ${{escapeHtml(record.reason || "")}}
preview:
${{escapeHtml(record.csv_preview || "No CSV preview")}}</code>
                </details>
              `;
              card.append(image, body);
              return card;
            }}

            function escapeHtml(value) {{
              return String(value)
                .replaceAll("&", "&amp;")
                .replaceAll("<", "&lt;")
                .replaceAll(">", "&gt;")
                .replaceAll('"', "&quot;");
            }}

            function render() {{
              renderTree();
              renderGrid();
            }}

            document.getElementById("search").addEventListener("input", (event) => {{
              state.query = event.target.value;
              renderGrid();
            }});
            document.getElementById("tile").addEventListener("input", (event) => {{
              state.tile = Number(event.target.value);
              renderGrid();
            }});
            document.getElementById("expand").addEventListener("click", () => {{
              state.expanded = new Set(folderMap.keys());
              renderTree();
            }});
            document.getElementById("collapse").addEventListener("click", () => {{
              state.expanded = new Set(["."]);
              renderTree();
            }});
            document.getElementById("clear").addEventListener("click", () => {{
              state.selected = new Set();
              render();
            }});

            render();
          </script>
        </body>
        </html>
        """
    )


def _record_payload(record: PlotRecord) -> dict[str, object]:
    csv_preview = _csv_preview(record)
    return {
        "id": record.plot_id,
        "name": record.image.relative_path.name,
        "kind": record.image.suffix.removeprefix(".").upper(),
        "image_path": record.image.relative_path.as_posix(),
        "csv_path": record.csv.relative_path.as_posix() if record.csv else None,
        "confidence": record.association_confidence.value,
        "reason": record.association_reason,
        "image_src": _image_data_uri(
            record.cache.cache_path if record.cache and record.cache.cache_path else record.image.path
        ),
        "cache_path": record.cache.cache_path.as_posix()
        if record.cache and record.cache.cache_path
        else None,
        "csv_preview": csv_preview,
    }


def _image_data_uri(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".svg":
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:image/svg+xml;base64,{encoded}"
    mime = "image/png" if suffix == ".png" else "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _csv_preview(record: PlotRecord) -> str | None:
    if record.csv is None:
        return None
    try:
        frame = pd.read_csv(record.csv.path, nrows=5)
    except Exception as exc:
        return f"CSV preview failed: {html.escape(str(exc))}"
    return frame.to_string(index=False)


if __name__ == "__main__":
    main()

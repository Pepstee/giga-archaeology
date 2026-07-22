#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";

function read(root, name) {
  return fs.readFileSync(path.join(root, name), "utf8");
}

function plain(value) {
  return JSON.parse(JSON.stringify(value, (_key, item) => {
    if (item instanceof Set) return [...item];
    return item;
  }));
}

function run(source, trailer, sandbox = {}) {
  vm.runInNewContext(`${source}\n${trailer}`, sandbox, {
    timeout: 2_000,
    contextCodeGeneration: { strings: false, wasm: false },
  });
  return plain(sandbox.__skilltree_export__);
}

function extractTreeProgram(html) {
  const start = html.indexOf("const L =");
  const marker = html.indexOf("const TREE =", start);
  const arrayStart = html.indexOf("[", marker);
  if (start < 0 || marker < 0 || arrayStart < 0) {
    throw new Error("TREE declaration not found in map.html");
  }

  let depth = 0;
  let quote = null;
  let escaped = false;
  let lineComment = false;
  let blockComment = false;
  let end = -1;
  for (let i = arrayStart; i < html.length; i += 1) {
    const ch = html[i];
    const next = html[i + 1];
    if (lineComment) {
      if (ch === "\n") lineComment = false;
      continue;
    }
    if (blockComment) {
      if (ch === "*" && next === "/") {
        blockComment = false;
        i += 1;
      }
      continue;
    }
    if (quote) {
      if (escaped) escaped = false;
      else if (ch === "\\") escaped = true;
      else if (ch === quote) quote = null;
      continue;
    }
    if (ch === "/" && next === "/") {
      lineComment = true;
      i += 1;
      continue;
    }
    if (ch === "/" && next === "*") {
      blockComment = true;
      i += 1;
      continue;
    }
    if (ch === "'" || ch === '"' || ch === "`") {
      quote = ch;
      continue;
    }
    if (ch === "[") depth += 1;
    if (ch === "]") {
      depth -= 1;
      if (depth === 0) {
        end = i + 1;
        break;
      }
    }
  }
  if (end < 0) throw new Error("TREE array is not balanced");
  const semicolon = html.indexOf(";", end);
  return html.slice(start, semicolon + 1);
}

const root = process.argv[2];
if (!root) throw new Error("Usage: extract_skilltree_data.mjs RAW_DIR");

const content = run(
  read(root, "content.js"),
  "globalThis.__skilltree_export__ = { HUB, PLAYBOOK, HUB_ENTRY, HUMAN_DEFAULT, FOUNDATION };",
);
const skillMeta = run(
  read(root, "skill-meta.js"),
  "globalThis.__skilltree_export__ = SKILL_META;",
);
const previewSandbox = { window: {} };
const skillPreviews = run(
  read(root, "skill-previews.js"),
  "globalThis.__skilltree_export__ = window.SKILL_PREVIEWS;",
  previewSandbox,
);
const tree = run(
  extractTreeProgram(read(root, "map.html")),
  "globalThis.__skilltree_export__ = TREE;",
);

process.stdout.write(JSON.stringify({
  tree,
  playbook: content.PLAYBOOK,
  hub: content.HUB,
  hub_entry: content.HUB_ENTRY,
  human_defaults: content.HUMAN_DEFAULT,
  foundation_jobs: content.FOUNDATION,
  skill_meta: skillMeta,
  skill_previews: skillPreviews,
}));

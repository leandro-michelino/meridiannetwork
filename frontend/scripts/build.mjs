import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const root = resolve(scriptDir, "../..");
const sourcePath = resolve(root, "oci_network_monitor_dashboard_v2.html");
const distDir = resolve(root, "frontend/dist");
const outPath = resolve(distDir, "index.html");
const versionPath = resolve(distDir, "version.json");

function git(args) {
  return execFileSync("git", args, { cwd: root, encoding: "utf8" }).trim();
}

function optionalGit(args, fallback) {
  try {
    return git(args);
  } catch {
    return fallback;
  }
}

const revision = process.env.MERIDIAN_BUILD_REVISION || optionalGit(["rev-parse", "HEAD"], "unknown");
const shortRevision =
  process.env.MERIDIAN_BUILD_SHORT_REVISION || optionalGit(["rev-parse", "--short=12", "HEAD"], revision.slice(0, 12));
const builtAt = process.env.MERIDIAN_BUILD_BUILT_AT || new Date().toISOString();
const dirty = optionalGit(["status", "--short"], "") !== "";

const buildInfo = {
  app: "meridian",
  artifact: "frontend",
  version: "0.1.0",
  revision,
  short_revision: shortRevision,
  built_at: builtAt,
  dirty,
};

let html = readFileSync(sourcePath, "utf8");
const meta = [
  `<meta name="meridian-build-revision" content="${shortRevision}">`,
  `<meta name="meridian-build-built-at" content="${builtAt}">`,
  `<script>window.MERIDIAN_BUILD=${JSON.stringify(buildInfo)};</script>`,
].join("\n");

if (html.includes("<!-- MERIDIAN_BUILD_INFO -->")) {
  html = html.replace("<!-- MERIDIAN_BUILD_INFO -->", meta);
} else {
  html = html.replace("</head>", `${meta}\n</head>`);
}

rmSync(distDir, { recursive: true, force: true });
mkdirSync(distDir, { recursive: true });
writeFileSync(outPath, html);
writeFileSync(versionPath, `${JSON.stringify(buildInfo, null, 2)}\n`);

console.log(`Built Meridian frontend ${shortRevision} -> ${distDir}`);

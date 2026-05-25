import { mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createBuildInfo } from "../src/build-info.mjs";
import { injectBuildInfo } from "../src/html-artifact.mjs";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const root = resolve(scriptDir, "../..");
const sourcePath = resolve(root, "oci_network_monitor_dashboard_v2.html");
const distDir = resolve(root, "frontend/dist");
const outPath = resolve(distDir, "index.html");
const versionPath = resolve(distDir, "version.json");

const buildInfo = createBuildInfo(root);
const html = injectBuildInfo(readFileSync(sourcePath, "utf8"), buildInfo);

rmSync(distDir, { recursive: true, force: true });
mkdirSync(distDir, { recursive: true });
writeFileSync(outPath, html);
writeFileSync(versionPath, `${JSON.stringify(buildInfo, null, 2)}\n`);

console.log(`Built Meridian frontend ${buildInfo.short_revision} -> ${distDir}`);

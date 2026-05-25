import { execFileSync } from "node:child_process";

export function gitValue(root, args, fallback) {
  try {
    return execFileSync("git", args, { cwd: root, encoding: "utf8" }).trim();
  } catch {
    return fallback;
  }
}

export function createBuildInfo(root, env = process.env) {
  const revision = env.MERIDIAN_BUILD_REVISION || gitValue(root, ["rev-parse", "HEAD"], "unknown");
  const shortRevision =
    env.MERIDIAN_BUILD_SHORT_REVISION || gitValue(root, ["rev-parse", "--short=12", "HEAD"], revision.slice(0, 12));
  return {
    app: "meridian",
    artifact: "frontend",
    version: "0.1.0",
    revision,
    short_revision: shortRevision,
    built_at: env.MERIDIAN_BUILD_BUILT_AT || new Date().toISOString(),
    dirty: gitValue(root, ["status", "--short"], "") !== "",
  };
}

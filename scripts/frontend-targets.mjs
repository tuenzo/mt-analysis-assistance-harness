import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export const REPO_ROOT = path.resolve(__dirname, "..");
export const FRONTEND_ROOT = path.join(REPO_ROOT, "frontend");

export const DEFAULT_API_BASE = "http://127.0.0.1:18081";
export const DEFAULT_STABLE_URL = "http://localhost:3010/projects/demo-project/dashboard";
export const DEFAULT_TEST_ORIGIN = "http://127.0.0.1:4180";
export const DEFAULT_TEST_PATH = "/agent-analysis-test";

function normalizeBaseUrl(value) {
  return String(value || "").trim().replace(/\/+$/, "");
}

function withApiBase(url, apiBase) {
  const parsed = new URL(url);
  parsed.searchParams.set("api_base", normalizeBaseUrl(apiBase));
  return parsed.toString();
}

function readApiBase(env) {
  return normalizeBaseUrl(
    env.BAA_API_BASE || env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE,
  );
}

export function getFrontendTargets(env = process.env) {
  const apiBase = readApiBase(env);
  const stableUrl = env.BAA_STABLE_FRONTEND_URL || DEFAULT_STABLE_URL;
  const testOrigin = env.BAA_TEST_FRONTEND_ORIGIN || DEFAULT_TEST_ORIGIN;
  const testPath = env.BAA_TEST_FRONTEND_PATH || DEFAULT_TEST_PATH;
  const testUrl = env.BAA_TEST_FRONTEND_URL || withApiBase(`${testOrigin}${testPath}`, apiBase);
  const testHealthUrl = env.BAA_TEST_FRONTEND_HEALTH_URL || testUrl;

  return {
    manual: {
      name: "manual",
      label: "Manual stable frontend",
      url: stableUrl,
      healthUrl: stableUrl,
      start: false,
    },
    stable: {
      name: "stable",
      label: "Manual stable frontend",
      url: stableUrl,
      healthUrl: stableUrl,
      start: false,
    },
    test: {
      name: "test",
      label: "Dedicated harness test frontend",
      url: testUrl,
      healthUrl: testHealthUrl,
      start: true,
      command: [
        "node",
        "scripts/serve-frontend.mjs",
        "--host",
        "127.0.0.1",
        "--port",
        "4180",
        "--name",
        "test",
      ].join(" "),
    },
  };
}

export function resolveFrontendTarget(env = process.env) {
  if (env.BAA_FRONTEND_URL) {
    const url = env.BAA_FRONTEND_URL;
    return {
      name: env.BAA_FRONTEND_TARGET || "custom",
      label: "Custom frontend",
      url,
      healthUrl: env.BAA_FRONTEND_HEALTH_URL || url,
      start: false,
    };
  }

  const targets = getFrontendTargets(env);
  const requested = String(env.BAA_FRONTEND_TARGET || "test").trim().toLowerCase();
  const target = targets[requested];
  if (!target) {
    const options = Object.keys(targets).join(", ");
    throw new Error(`Unknown BAA_FRONTEND_TARGET "${requested}". Expected one of: ${options}`);
  }
  return target;
}

import { spawn } from "node:child_process";
import { access } from "node:fs/promises";
import path from "node:path";
import { DEFAULT_API_BASE, FRONTEND_ROOT } from "./frontend-targets.mjs";
import { appendLifecycleEvent } from "./frontend-lifecycle.mjs";

const DEFAULTS = {
  host: "127.0.0.1",
  port: 4180,
  name: "test",
  mode: "start",
  apiBase: process.env.BAA_API_BASE || process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE,
};

function parseArgs(argv) {
  const config = { ...DEFAULTS };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (!arg.startsWith("--")) continue;
    const [key, inlineValue] = arg.slice(2).split("=", 2);
    const value = inlineValue ?? argv[i + 1];
    if (inlineValue === undefined) i += 1;
    if (key === "host") config.host = value;
    if (key === "port") config.port = Number(value);
    if (key === "name") config.name = value;
    if (key === "mode") config.mode = value;
    if (key === "api-base") config.apiBase = value;
  }
  if (!Number.isInteger(config.port) || config.port <= 0) {
    throw new Error(`Invalid --port: ${config.port}`);
  }
  if (!["start", "dev"].includes(config.mode)) {
    throw new Error(`Invalid --mode: ${config.mode}. Expected start or dev.`);
  }
  return config;
}

const config = parseArgs(process.argv.slice(2));
const frontendUrl = `http://${config.host}:${config.port}/agent-analysis-test?api_base=${encodeURIComponent(config.apiBase)}`;
const nextCli = path.join(FRONTEND_ROOT, "node_modules", "next", "dist", "bin", "next");

await access(nextCli).catch(() => {
  throw new Error(`Next CLI not found at ${nextCli}. Run npm install in ${FRONTEND_ROOT}.`);
});

await appendLifecycleEvent({
  source: "serve-frontend",
  event: "webserver_starting",
  runId: process.env.BAA_FRONTEND_RUN_ID || null,
  target: config.name,
  url: frontendUrl,
  apiBase: config.apiBase,
  mode: config.mode,
  cwd: FRONTEND_ROOT,
});

const child = spawn(
  process.execPath,
  [nextCli, config.mode, "--hostname", config.host, "--port", String(config.port)],
  {
    cwd: FRONTEND_ROOT,
    env: {
      ...process.env,
      NEXT_PUBLIC_API_BASE_URL: config.apiBase,
      PORT: String(config.port),
    },
    stdio: "inherit",
  },
);

console.log(`[${config.name}] harness frontend: ${frontendUrl}`);
console.log(`[${config.name}] backend api: ${config.apiBase}`);
console.log(`[${config.name}] next mode: ${config.mode}`);

let shuttingDown = false;

async function shutdown(signal) {
  if (shuttingDown) return;
  shuttingDown = true;
  await appendLifecycleEvent({
    source: "serve-frontend",
    event: "webserver_stop_requested",
    runId: process.env.BAA_FRONTEND_RUN_ID || null,
    target: config.name,
    url: frontendUrl,
    signal,
  }).catch(() => {});
  child.kill(signal);
  setTimeout(() => process.exit(0), 5_000).unref();
}

child.on("spawn", () => {
  appendLifecycleEvent({
    source: "serve-frontend",
    event: "webserver_start",
    runId: process.env.BAA_FRONTEND_RUN_ID || null,
    target: config.name,
    url: frontendUrl,
    apiBase: config.apiBase,
    mode: config.mode,
    cwd: FRONTEND_ROOT,
  }).catch(() => {});
});

child.on("exit", async (code, signal) => {
  await appendLifecycleEvent({
    source: "serve-frontend",
    event: "webserver_exit",
    runId: process.env.BAA_FRONTEND_RUN_ID || null,
    target: config.name,
    url: frontendUrl,
    exitCode: code,
    signal,
  }).catch(() => {});
  if (shuttingDown) process.exit(0);
  process.exit(code ?? 1);
});

child.on("error", async (error) => {
  await appendLifecycleEvent({
    source: "serve-frontend",
    event: "webserver_error",
    runId: process.env.BAA_FRONTEND_RUN_ID || null,
    target: config.name,
    url: frontendUrl,
    error: error instanceof Error ? error.message : String(error),
  }).catch(() => {});
  throw error;
});

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => {
    shutdown(signal).catch(() => process.exit(1));
  });
}

import { spawn } from "node:child_process";
import { randomUUID } from "node:crypto";
import path from "node:path";
import { FRONTEND_ROOT, REPO_ROOT, resolveFrontendTarget } from "./frontend-targets.mjs";
import { appendLifecycleEvent } from "./frontend-lifecycle.mjs";

function parseArgs(argv) {
  const args = { playwright: [] };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--") {
      args.playwright.push(...argv.slice(i + 1));
      break;
    }
    if (arg === "--target") {
      args.target = argv[i + 1];
      i += 1;
      continue;
    }
    if (arg.startsWith("--target=")) {
      args.target = arg.slice("--target=".length);
      continue;
    }
    args.playwright.push(arg);
  }
  return args;
}

const args = parseArgs(process.argv.slice(2));
const env = { ...process.env };
if (args.target) env.BAA_FRONTEND_TARGET = args.target;

const target = resolveFrontendTarget(env);
const runId = randomUUID();
env.BAA_FRONTEND_TARGET = target.name;
env.BAA_FRONTEND_RUN_ID = runId;
env.BAA_RESOLVED_FRONTEND_URL = target.url;
env.BAA_RESOLVED_FRONTEND_HEALTH_URL = target.healthUrl || target.url;

console.log(`[e2e] target=${target.name} url=${target.url}`);
await appendLifecycleEvent({
  source: "run-e2e",
  event: "target_resolved",
  runId,
  target: target.name,
  url: target.url,
  healthUrl: target.healthUrl || null,
  start: Boolean(target.start),
});

const playwrightCli = path.join(FRONTEND_ROOT, "node_modules", "@playwright", "test", "cli.js");
const startedAt = Date.now();
await appendLifecycleEvent({
  source: "run-e2e",
  event: "e2e_start",
  runId,
  target: target.name,
  url: target.url,
  healthUrl: target.healthUrl || null,
});

const child = spawn(
  process.execPath,
  [playwrightCli, "test", "-c", "frontend/playwright.config.mjs", ...args.playwright],
  {
    cwd: REPO_ROOT,
    env,
    stdio: "inherit",
  },
);

child.on("exit", async (code, signal) => {
  await appendLifecycleEvent({
    source: "run-e2e",
    event: "e2e_exit",
    runId,
    target: target.name,
    url: target.url,
    healthUrl: target.healthUrl || null,
    exitCode: code,
    signal,
    durationMs: Date.now() - startedAt,
  }).catch(() => {});
  if (signal) {
    console.error(`[e2e] exited by signal ${signal}`);
    process.exit(1);
  }
  process.exit(code ?? 1);
});

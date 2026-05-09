import { appendFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { getFrontendTargets, REPO_ROOT, resolveFrontendTarget } from "./frontend-targets.mjs";

export const FRONTEND_RUNTIME_DIR = path.join(REPO_ROOT, ".codex-run", "frontend");
export const FRONTEND_LIFECYCLE_LOG = path.join(FRONTEND_RUNTIME_DIR, "frontend-lifecycle.jsonl");

function parseArgs(argv) {
  const args = {
    command: argv[0] || "probe",
    target: "test",
    intervalMs: 30_000,
    timeoutMs: 5_000,
  };
  for (let i = 1; i < argv.length; i += 1) {
    const arg = argv[i];
    if (!arg.startsWith("--")) continue;
    const [key, inlineValue] = arg.slice(2).split("=", 2);
    const value = inlineValue ?? argv[i + 1];
    if (inlineValue === undefined) i += 1;
    if (key === "target") args.target = value;
    if (key === "event") args.event = value;
    if (key === "url") args.url = value;
    if (key === "interval-ms") args.intervalMs = Number(value);
    if (key === "timeout-ms") args.timeoutMs = Number(value);
    if (key === "message") args.message = value;
  }
  return args;
}

function targetFromName(name, url) {
  if (url) return { name: name || "custom", url, healthUrl: url, start: false };
  if (name === "all") return null;
  return resolveFrontendTarget({ ...process.env, BAA_FRONTEND_TARGET: name });
}

function selectedTargets(args) {
  if (args.target === "all") {
    const targets = getFrontendTargets(process.env);
    return [targets.stable, targets.test];
  }
  return [targetFromName(args.target, args.url)];
}

export async function appendLifecycleEvent(event) {
  await mkdir(FRONTEND_RUNTIME_DIR, { recursive: true });
  const line = {
    ts: new Date().toISOString(),
    project: "meituancomp-analysis-assistance-harness",
    pid: process.pid,
    ...event,
  };
  await appendFile(FRONTEND_LIFECYCLE_LOG, `${JSON.stringify(line)}\n`, "utf8");
  return line;
}

export async function probeFrontendUrl(url, timeoutMs = 5_000) {
  const started = Date.now();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { signal: controller.signal, cache: "no-store" });
    return {
      ok: response.ok,
      httpStatus: response.status,
      latencyMs: Date.now() - started,
    };
  } catch (error) {
    return {
      ok: false,
      httpStatus: null,
      latencyMs: Date.now() - started,
      error: error instanceof Error ? error.message : String(error),
    };
  } finally {
    clearTimeout(timer);
  }
}

export async function recordFrontendProbe(target, options = {}) {
  const url = target.healthUrl || target.url;
  const result = await probeFrontendUrl(url, options.timeoutMs);
  return appendLifecycleEvent({
    source: options.source || "frontend-lifecycle",
    event: result.ok ? "health_ok" : "health_fail",
    target: target.name,
    url: target.url,
    healthUrl: url,
    ok: result.ok,
    httpStatus: result.httpStatus,
    latencyMs: result.latencyMs,
    error: result.error,
  });
}

async function runProbe(args) {
  for (const target of selectedTargets(args)) {
    const line = await recordFrontendProbe(target, {
      timeoutMs: args.timeoutMs,
      source: "probe",
    });
    console.log(JSON.stringify(line));
  }
}

async function runRecord(args) {
  const target = targetFromName(args.target, args.url);
  const line = await appendLifecycleEvent({
    source: "record",
    event: args.event || "note",
    target: target.name,
    url: target.url,
    message: args.message || "",
  });
  console.log(JSON.stringify(line));
}

async function runMonitor(args) {
  const targets = selectedTargets(args);
  await appendLifecycleEvent({
    source: "monitor",
    event: "monitor_start",
    target: args.target,
    url: args.url || targets.map((target) => target.url).join(","),
    intervalMs: args.intervalMs,
  });

  const tick = async () => {
    for (const target of targets) {
      await recordFrontendProbe(target, { timeoutMs: args.timeoutMs, source: "monitor" });
    }
  };

  await tick();
  const timer = setInterval(() => {
    tick().catch((error) => {
      appendLifecycleEvent({
        source: "monitor",
        event: "monitor_error",
        target: args.target,
        error: error instanceof Error ? error.message : String(error),
      }).catch(() => {});
    });
  }, args.intervalMs);

  const shutdown = async (signal) => {
    clearInterval(timer);
    await appendLifecycleEvent({
      source: "monitor",
      event: "monitor_stop",
      target: args.target,
      signal,
    });
    process.exit(0);
  };
  process.on("SIGINT", () => shutdown("SIGINT"));
  process.on("SIGTERM", () => shutdown("SIGTERM"));
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const args = parseArgs(process.argv.slice(2));
  const runners = { probe: runProbe, record: runRecord, monitor: runMonitor };
  const runner = runners[args.command];
  if (!runner) {
    console.error(`Unknown command "${args.command}". Expected: probe, record, monitor`);
    process.exit(1);
  }
  runner(args).catch((error) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exit(1);
  });
}

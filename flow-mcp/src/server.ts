import { spawn } from "node:child_process";
import { randomBytes } from "node:crypto";
import { createReadStream, existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import { basename, extname, join, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { z } from "zod";
import { CACHE_DIR as CAPTIONS_DIR } from "./captions.js";
import { HOME_DIR } from "./chrome.js";
import { OUTPUT_ROOT, shapes, type Core } from "./core.js";

export const PORT = Number(process.env.FLOW_MCP_PORT ?? 8787);
export let ACTUAL_PORT = PORT;
export const TOKEN_FILE = join(HOME_DIR, "token");
const UPLOAD_DIR = join(HOME_DIR, "uploads");
const STUDIO_HTML = fileURLToPath(new URL("../studio/index.html", import.meta.url));
const MAX_UPLOAD = 200 * 1024 * 1024;

const MIME: Record<string, string> = {
  ".mp4": "video/mp4", ".webm": "video/webm", ".mov": "video/quicktime", ".gif": "image/gif",
  ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp",
  ".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4",
};

const json = (res: ServerResponse, code: number, data: unknown) => {
  res.writeHead(code, { "content-type": "application/json", "cache-control": "no-store" });
  res.end(JSON.stringify(data));
};

function readBody(req: IncomingMessage, limit: number): Promise<Buffer> {
  return new Promise((ok, fail) => {
    const chunks: Buffer[] = [];
    let size = 0;
    req.on("data", (c: Buffer) => {
      size += c.length;
      if (size > limit) {
        fail(new Error("Body too large."));
        req.destroy();
      } else chunks.push(c);
    });
    req.on("end", () => ok(Buffer.concat(chunks)));
    req.on("error", fail);
  });
}

const inside = (file: string, dir: string) => resolve(file).startsWith(resolve(dir) + sep);

function sendMedia(req: IncomingMessage, res: ServerResponse, file: string) {
  if (!(inside(file, OUTPUT_ROOT) || inside(file, UPLOAD_DIR) || inside(file, CAPTIONS_DIR)) || !existsSync(file)) return json(res, 404, { error: "Not found." });
  const { size } = statSync(file);
  const type = MIME[extname(file).toLowerCase()] ?? "application/octet-stream";
  const range = req.headers.range?.match(/bytes=(\d*)-(\d*)/);
  if (range) {
    const start = range[1] ? Number(range[1]) : 0;
    const end = range[2] ? Math.min(Number(range[2]), size - 1) : size - 1;
    res.writeHead(206, { "content-type": type, "accept-ranges": "bytes", "content-range": `bytes ${start}-${end}/${size}`, "content-length": end - start + 1 });
    return createReadStream(file, { start, end }).pipe(res);
  }
  res.writeHead(200, { "content-type": type, "accept-ranges": "bytes", "content-length": size });
  createReadStream(file).pipe(res);
}

export type ServerRole = "owner" | "client" | "none";

export function isPortFree(port: number): Promise<boolean> {
  return new Promise((resolve) => {
    const s = createServer();
    s.once("error", () => resolve(false));
    s.listen(port, "127.0.0.1", () => {
      s.close(() => resolve(true));
    });
  });
}

export async function findAvailablePort(startPort: number = 8787, maxPort: number = 8899): Promise<number> {
  for (let p = startPort; p <= maxPort; p++) {
    if (await isPortFree(p)) return p;
  }
  throw new Error(`No available ports found between ${startPort} and ${maxPort}`);
}

// Serves the Studio panel and a JSON API on localhost. Returns "client" when another flow-mcp process already
// owns the port (that process owns the Flow tab and the queue), "none" when the port is taken by something else.
export async function startServer(core: Core, preferredPort?: number, autoPort?: boolean): Promise<ServerRole> {
  mkdirSync(UPLOAD_DIR, { recursive: true });
  let portToUse = preferredPort ?? PORT;

  if (autoPort && !(await isPortFree(portToUse))) {
    portToUse = await findAvailablePort(portToUse + 1);
  }

  ACTUAL_PORT = portToUse;
  const token = randomBytes(24).toString("hex");
  const allowedHosts = new Set([
    `127.0.0.1:${portToUse}`,
    `localhost:${portToUse}`,
    `127.0.0.1:${PORT}`,
    `localhost:${PORT}`,
  ]);

  const server = createServer(async (req, res) => {
    try {
      // The Host check blocks DNS-rebinding; the token blocks other local pages from driving the queue.
      if (!allowedHosts.has(req.headers.host ?? "")) return json(res, 403, { error: "Bad host." });
      const url = new URL(req.url ?? "/", `http://${req.headers.host}`);

      if (req.method === "GET" && url.pathname === "/api/health") return json(res, 200, { name: "flow-mcp", port: portToUse });
      if (url.pathname === "/favicon.ico") return void res.writeHead(204).end();
      if (req.method === "GET" && url.pathname === "/") {
        res.writeHead(200, { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" });
        return res.end(readFileSync(STUDIO_HTML, "utf8").replace("__FLOW_TOKEN__", token));
      }

      const given = req.headers["x-flow-token"] ?? url.searchParams.get("token");
      if (given !== token) return json(res, 401, { error: "Missing or wrong token." });

      // Spawn another server instance on a new port for parallel video generation
      if (req.method === "POST" && url.pathname === "/api/spawn_server") {
        try {
          const nextPort = await findAvailablePort(ACTUAL_PORT + 1);
          const studioScript = fileURLToPath(new URL("./studio.js", import.meta.url));
          const child = spawn(process.execPath, [studioScript, "--port", String(nextPort)], {
            detached: true,
            stdio: "ignore",
            windowsHide: true,
          });
          child.unref();

          // Wait up to 3 seconds for it to start
          for (let i = 0; i < 15; i++) {
            await new Promise((r) => setTimeout(r, 200));
            const ok = await fetch(`http://127.0.0.1:${nextPort}/api/health`, { signal: AbortSignal.timeout(1000) })
              .then((r) => r.ok)
              .catch(() => false);
            if (ok) break;
          }

          return json(res, 200, { ok: true, port: nextPort, url: `http://127.0.0.1:${nextPort}` });
        } catch (err: any) {
          return json(res, 500, { error: err.message });
        }
      }

      if (req.method === "GET" && url.pathname === "/media") return sendMedia(req, res, url.searchParams.get("path") ?? "");

      if (req.method === "POST" && url.pathname === "/api/upload") {
        const name = basename(url.searchParams.get("name") ?? "upload").replace(/[^\w.-]+/g, "_");
        const path = join(UPLOAD_DIR, `${randomBytes(4).toString("hex")}-${name}`);
        writeFileSync(path, await readBody(req, MAX_UPLOAD));
        return json(res, 200, { path });
      }

      const method = url.pathname.match(/^\/api\/(\w+)$/)?.[1] as keyof Core | undefined;
      if (req.method === "POST" && method && typeof core[method] === "function") {
        const raw = (await readBody(req, 1024 * 1024)).toString() || "{}";
        const shape = (shapes as Record<string, z.ZodRawShape>)[method];
        const args = shape ? z.object(shape).parse(JSON.parse(raw)) : undefined;
        return json(res, 200, await (core[method] as (a: unknown) => Promise<unknown>)(args));
      }
      json(res, 404, { error: "Not found." });
    } catch (err) {
      const message = err instanceof z.ZodError ? err.issues.map((i) => `${i.path.join(".")}: ${i.message}`).join("; ") : err instanceof Error ? err.message : String(err);
      json(res, 400, { error: message });
    }
  });

  const listening = await new Promise<boolean>((ok) => {
    server.once("error", () => ok(false));
    server.listen(portToUse, "127.0.0.1", () => ok(true));
  });

  if (listening) {
    mkdirSync(HOME_DIR, { recursive: true });
    if (portToUse === PORT) {
      writeFileSync(TOKEN_FILE, token, { mode: 0o600 });
    }
    writeFileSync(join(HOME_DIR, `token-${portToUse}`), token, { mode: 0o600 });
    return "owner";
  }

  // If a specific non-default port was requested and failed
  if (preferredPort && preferredPort !== PORT) {
    return "none";
  }

  // The default port is taken. Who has it matters:
  for (let attempt = 0; attempt < 8; attempt++) {
    const other = (await fetch(`http://127.0.0.1:${PORT}/api/health`, { signal: AbortSignal.timeout(3000) }).then(
      (r) => r.json(),
      () => null,
    )) as { name?: string } | null;
    if (other?.name === "flow-mcp") return "client";
    if (other) return "none";
    await new Promise((r) => setTimeout(r, 1500));
  }
  return "client";
}

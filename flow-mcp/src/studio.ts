#!/usr/bin/env node
// Standalone Studio: runs the panel. Supports parallel local servers for side-by-side video generation.
import { LocalCore } from "./core.js";
import { ACTUAL_PORT, findAvailablePort, PORT, startServer } from "./server.js";
import { openUrl } from "./platform.js";

const args = process.argv.slice(2);
const portFlagIndex = args.indexOf("--port");
const requestedPort = portFlagIndex !== -1 && args[portFlagIndex + 1] ? Number(args[portFlagIndex + 1]) : undefined;
const isNew = args.includes("--new") || args.includes("-n") || Boolean(process.env.FLOW_STUDIO_NEW);

let targetPort = requestedPort ?? PORT;
if (isNew && !requestedPort) {
  targetPort = await findAvailablePort(PORT + 1);
}

const role = await startServer(new LocalCore(), targetPort, isNew);
const url = `http://127.0.0.1:${ACTUAL_PORT}`;

if (role === "none") {
  console.error(`Port ${targetPort} is used by another program. Set FLOW_MCP_PORT to a free port or pass --new.`);
  process.exit(1);
}

if (role === "owner") {
  console.log(`Flow Studio running at ${url} (Ctrl+C to stop)`);
  if (ACTUAL_PORT !== PORT) {
    console.log(`[Parallel Instance] Running on port ${ACTUAL_PORT} for side-by-side video generation.`);
  } else {
    console.log(`Tip: run "npm run studio:new" to launch another independent server on a new port for side-by-side video generation.`);
  }
} else {
  console.log(`Flow Studio is already served by another flow-mcp process at ${url}`);
  console.log(`To open a NEW parallel server for side-by-side video generation, run: node dist/studio.js --new`);
}

openUrl(url);
if (role === "client" && !isNew) process.exit(0);

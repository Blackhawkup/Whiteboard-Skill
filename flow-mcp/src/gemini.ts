import { execFile } from "node:child_process";
import { chmodSync, existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { promisify } from "node:util";
import { HOME_DIR } from "./chrome.js";

const run = promisify(execFile);
const FFMPEG = process.env.FLOW_MCP_FFMPEG ?? "ffmpeg";
const KEY_FILE = join(HOME_DIR, "gemini-key");
const MODEL = process.env.FLOW_MCP_GEMINI_TTS ?? "gemini-2.5-flash-preview-tts";

// Gemini's prebuilt voices. Flow draws on the same set, so a narration made here matches one made in Flow.
export const GEMINI_VOICES = [
  { name: "Zephyr", description: "bright" }, { name: "Puck", description: "upbeat" },
  { name: "Charon", description: "informative" }, { name: "Kore", description: "firm" },
  { name: "Fenrir", description: "excitable" }, { name: "Leda", description: "youthful" },
  { name: "Orus", description: "firm" }, { name: "Aoede", description: "breezy" },
  { name: "Callirrhoe", description: "easy-going" }, { name: "Autonoe", description: "bright" },
  { name: "Enceladus", description: "breathy" }, { name: "Iapetus", description: "clear" },
  { name: "Umbriel", description: "easy-going" }, { name: "Algieba", description: "smooth" },
  { name: "Despina", description: "smooth" }, { name: "Erinome", description: "clear" },
  { name: "Algenib", description: "gravelly" }, { name: "Rasalgethi", description: "informative" },
  { name: "Laomedeia", description: "upbeat" }, { name: "Achernar", description: "soft" },
  { name: "Alnilam", description: "firm" }, { name: "Schedar", description: "even" },
  { name: "Gacrux", description: "mature" }, { name: "Pulcherrima", description: "forward" },
  { name: "Achird", description: "friendly" }, { name: "Zubenelgenubi", description: "casual" },
  { name: "Vindemiatrix", description: "gentle" }, { name: "Sadachbia", description: "lively" },
  { name: "Sadaltager", description: "knowledgeable" }, { name: "Sulafat", description: "warm" },
];

let activeKeyIndex = 0;

export function parseKeys(raw: string): string[] {
  if (!raw) return [];
  return raw
    .split(/[\r\n,;\s]+/)
    .map((k) => k.trim())
    .filter((k) => k.length >= 20 && !/^(YOUR|PASTE|<|\$)/i.test(k) && !/_KEY|KEY_HERE|EXAMPLE/i.test(k));
}

// Collects all configured Gemini API keys (from environment and key file), preserving unique order.
export function geminiKeys(): string[] {
  const envKeys = [
    ...(process.env.GEMINI_API_KEYS ? parseKeys(process.env.GEMINI_API_KEYS) : []),
    ...(process.env.GEMINI_API_KEY ? parseKeys(process.env.GEMINI_API_KEY) : []),
  ];
  const fileKeys = existsSync(KEY_FILE) ? parseKeys(readFileSync(KEY_FILE, "utf8")) : [];
  return Array.from(new Set([...envKeys, ...fileKeys]));
}

// Returns the current active Gemini key, or first available.
export const geminiKey = (): string | undefined => {
  const keys = geminiKeys();
  if (keys.length === 0) return undefined;
  if (activeKeyIndex >= keys.length) activeKeyIndex = 0;
  return keys[activeKeyIndex];
};

// Saves user key(s) from the panel. Accepts single key or multiple keys (separated by newline/comma).
// Verifies keys against Google before saving.
export async function saveGeminiKey(raw: string): Promise<{ saved: true; ending: string; count: number; endings: string[] }> {
  const candidates = parseKeys(raw);
  if (candidates.length === 0) {
    throw new Error("No valid Google AI Studio key found. Copy your key(s) from aistudio.google.com/apikey (paste one or more, one per line).");
  }

  const validKeys: string[] = [];
  const errors: string[] = [];

  for (const k of candidates) {
    if (!/^[A-Za-z0-9._~+/=-]{20,512}$/.test(k)) {
      errors.push(`Key ...${k.slice(-4)} has invalid characters`);
      continue;
    }
    const res = await fetch("https://generativelanguage.googleapis.com/v1beta/models?pageSize=1", {
      headers: { "x-goog-api-key": k },
    }).catch(() => null);

    if (!res) {
      errors.push(`Could not reach Google to verify key ...${k.slice(-4)}`);
      continue;
    }
    if (!res.ok) {
      errors.push(`Google rejected key ...${k.slice(-4)} (${res.status})`);
      continue;
    }
    validKeys.push(k);
  }

  if (validKeys.length === 0) {
    throw new Error(`Google rejected all supplied keys:\n${errors.join("\n")}`);
  }

  mkdirSync(dirname(KEY_FILE), { recursive: true });
  writeFileSync(KEY_FILE, validKeys.join("\n"), { mode: 0o600 });
  try {
    chmodSync(KEY_FILE, 0o600);
  } catch {}

  activeKeyIndex = 0;
  const endings = validKeys.map((k) => k.slice(-4));
  return {
    saved: true,
    ending: endings.join(", "),
    count: validKeys.length,
    endings,
  };
}

interface TtsPart {
  inlineData?: { mimeType?: string; data?: string };
}

// Speaks a line with Gemini's TTS. Supports multiple pooled API keys with automatic failover
// if quota limits (HTTP 429 / 403 / RESOURCE_EXHAUSTED) are hit.
export async function speakWithGemini(
  text: string,
  voice: string,
  target: string,
  style?: string,
): Promise<{ output: string; duration: number }> {
  const keys = geminiKeys();
  if (keys.length === 0) {
    const placeholder = existsSync(KEY_FILE) && readFileSync(KEY_FILE, "utf8").trim().length > 0;
    throw new Error(
      (placeholder
        ? `The key file still holds placeholder text, not a key.\n\n`
        : `No Gemini key yet.\n\n`) +
        `1. Open aistudio.google.com/apikey and click "Create API key".\n` +
        `2. Copy your key(s) (you can add multiple keys, one per line).\n` +
        `3. Paste into Flow Studio: Voice tab -> Google AI Studio key -> Save key. Keys auto-rotate if quota runs out.`,
    );
  }

  const prompt = style ? `Say ${style}: ${text}` : text;
  let lastError: Error | null = null;
  const startIndex = activeKeyIndex % keys.length;

  for (let attempt = 0; attempt < keys.length; attempt++) {
    const currentIndex = (startIndex + attempt) % keys.length;
    const currentKey = keys[currentIndex];
    const keyEnding = currentKey.slice(-4);

    try {
      const res = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent`, {
        method: "POST",
        headers: { "content-type": "application/json", "x-goog-api-key": currentKey },
        body: JSON.stringify({
          contents: [{ parts: [{ text: prompt }] }],
          generationConfig: {
            responseModalities: ["AUDIO"],
            speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: voice } } },
          },
        }),
      });

      const body = (await res.json()) as {
        error?: { code?: number; message?: string; status?: string };
        candidates?: { content?: { parts?: TtsPart[] } }[];
      };

      if (!res.ok) {
        const isQuotaOrLimit =
          res.status === 429 ||
          res.status === 403 ||
          body.error?.status === "RESOURCE_EXHAUSTED" ||
          /quota|rate limit|exhausted|capacity/i.test(body.error?.message ?? "");

        if (isQuotaOrLimit && keys.length > 1) {
          console.warn(
            `[Flow Gemini TTS] Key ...${keyEnding} exhausted (HTTP ${res.status}: ${body.error?.message ?? "Quota"}). Rotating to next key...`,
          );
          lastError = new Error(`Key ...${keyEnding} exhausted (${res.status}): ${body.error?.message ?? "Quota"}`);
          activeKeyIndex = (currentIndex + 1) % keys.length;
          continue;
        }
        throw new Error(`Gemini TTS refused this take (${res.status}): ${body.error?.message ?? "no detail"}`);
      }

      const part = body.candidates?.[0]?.content?.parts?.find((p) => p.inlineData?.data);
      if (!part?.inlineData?.data) throw new Error("Gemini returned no audio for this line.");

      // Key succeeded: keep it as active
      activeKeyIndex = currentIndex;

      // The audio comes back as raw signed 16-bit PCM, so the sample rate has to come from the mime type.
      const rate = Number(part.inlineData.mimeType?.match(/rate=(\d+)/)?.[1] ?? 24000);
      const raw = target.replace(/\.\w+$/, "") + ".pcm";
      writeFileSync(raw, Buffer.from(part.inlineData.data, "base64"));
      await run(FFMPEG, [
        "-y", "-f", "s16le", "-ar", String(rate), "-ac", "1", "-i", raw,
        "-af", "highpass=f=80,loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000", "-ac", "2", target,
      ]);
      const { stdout } = await run("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", target]);
      const duration = Number(stdout.trim());
      try {
        rmSync(raw, { force: true });
      } catch {}
      return { output: target, duration };
    } catch (err: any) {
      lastError = err;
      if (keys.length > 1 && attempt < keys.length - 1) {
        console.warn(`[Flow Gemini TTS] Error with key ...${keyEnding}: ${err.message}. Rotating to next key...`);
        activeKeyIndex = (currentIndex + 1) % keys.length;
        continue;
      }
      throw err;
    }
  }

  throw new Error(`All ${keys.length} Google AI Studio keys failed or were exhausted. Last error: ${lastError?.message}`);
}

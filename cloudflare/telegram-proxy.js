/**
 * Cloudflare Worker — Telegram Bot API proxy (Russia-safe).
 * Paste into Cloudflare dashboard → Workers → Edit code → Deploy.
 */

const SLOW_METHODS = /\/(sendPhoto|sendVoice|sendDocument|sendAudio|sendVideo|sendVideoNote|sendSticker|sendAnimation|setWebhook)$/i;

export default {
  async fetch(request) {
    if (request.method === "OPTIONS") {
      return new Response(null, {
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
          "Access-Control-Allow-Headers": "*",
        },
      });
    }

    const url = new URL(request.url);
    url.hostname = "api.telegram.org";

    const isFileDownload = url.pathname.includes("/file/bot");
    const isSlowUpload = SLOW_METHODS.test(url.pathname);
    const timeoutMs = isFileDownload || isSlowUpload ? 120_000 : 30_000;

    const headers = new Headers(request.headers);
    headers.delete("host");

    const init = { method: request.method, headers };

    if (request.method !== "GET" && request.method !== "HEAD") {
      const body = await request.arrayBuffer();
      init.body = body;
      if (body.byteLength > 0) {
        headers.set("Content-Length", String(body.byteLength));
      }
    }

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(url.toString(), {
        ...init,
        signal: controller.signal,
      });

      const body = await response.arrayBuffer();

      const outHeaders = new Headers();
      const contentType = response.headers.get("Content-Type");
      if (contentType) outHeaders.set("Content-Type", contentType);
      const contentLength = response.headers.get("Content-Length");
      if (contentLength) outHeaders.set("Content-Length", contentLength);
      outHeaders.set("Access-Control-Allow-Origin", "*");

      return new Response(body, { status: response.status, headers: outHeaders });
    } finally {
      clearTimeout(timer);
    }
  },
};

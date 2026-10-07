"use client";

import { useEffect, useState } from "react";

/** Shows the configured extraction model, or a fixed label. */
export default function EnginePill({ apiBaseUrl, label }: { apiBaseUrl: string; label?: string }) {
  const [text, setText] = useState(label ?? "engine: …");

  useEffect(() => {
    if (label) {
      setText(label);
      return;
    }
    let alive = true;
    const controller = new AbortController();

    async function load() {
      try {
        const response = await fetch(`${apiBaseUrl}/extract/config`, { signal: controller.signal });
        const config = (await response.json()) as { model?: string };
        if (alive) setText(`engine: ${config.model ?? "unknown"}`);
      } catch {
        if (alive) setText("engine: offline");
      }
    }

    void load();
    return () => {
      alive = false;
      controller.abort();
    };
  }, [apiBaseUrl, label]);

  return (
    <span className="pill stamp-violet" id="engine-pill">
      {text}
    </span>
  );
}

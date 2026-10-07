"use client";

import { useEffect, useRef, useState } from "react";

/** Renders a PDF to canvases with pdf.js — no browser PDF chrome. */
export default function PdfViewer({ url }: { url: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let loaded: { destroy?: () => void } | null = null;

    (async () => {
      try {
        const pdfjs = await import("pdfjs-dist");
        pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";
        const pdf = await pdfjs.getDocument({ url }).promise;
        loaded = pdf as unknown as { destroy?: () => void };
        const container = containerRef.current;
        if (!container || cancelled) return;
        container.replaceChildren();
        const ratio = window.devicePixelRatio || 1;
        for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber += 1) {
          if (cancelled) return;
          const page = await pdf.getPage(pageNumber);
          const base = page.getViewport({ scale: 1 });
          const scale = (container.clientWidth || base.width) / base.width;
          const viewport = page.getViewport({ scale: scale * ratio });
          const canvas = document.createElement("canvas");
          canvas.width = Math.floor(viewport.width);
          canvas.height = Math.floor(viewport.height);
          container.appendChild(canvas);
          await page.render({ canvas, canvasContext: canvas.getContext("2d")!, viewport }).promise;
        }
      } catch {
        if (!cancelled) setFailed(true);
      }
    })();

    return () => {
      cancelled = true;
      loaded?.destroy?.();
    };
  }, [url]);

  if (failed) {
    return <div className="doc-placeholder">PDF preview unavailable</div>;
  }
  return <div className="pdf-viewer" ref={containerRef} />;
}

import type { Metadata } from "next";

import "@docextract/ui/styles.css";

export const metadata: Metadata = { title: "Docextract" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

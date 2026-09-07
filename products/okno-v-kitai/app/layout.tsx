import type { Metadata } from "next";
import { SiteShell } from "@/components/site-shell";
import { UsageBeacon } from "@/components/usage-beacon";
import "./globals.css";

export const metadata: Metadata = {
  title: "Окно в Китай — автопром России и Китая",
  description:
    "Новости SHACMAN и Great Wall Motor, автомобильные выставки, поставщики и карта отрасли России и Китая.",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
  other: {
    "codex-preview": "development",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru">
      <body className="antialiased">
        <UsageBeacon />
        <SiteShell>{children}</SiteShell>
      </body>
    </html>
  );
}

import type { Metadata } from "next";
import "@fontsource/vazirmatn/400.css";
import "@fontsource/vazirmatn/600.css";
import "@fontsource/vazirmatn/800.css";
import "@openuidev/react-ui/index.css";
import "@xterm/xterm/css/xterm.css";
import { BOOTSTRAP } from "../lib/appearance";
import "./globals.css";
export const metadata: Metadata = { title: "CodeHarness", description: "Local coding assistant" };
export default function Layout({ children }: { children: React.ReactNode }) {
  return <html lang="fa" dir="rtl" suppressHydrationWarning>
    <head><script dangerouslySetInnerHTML={{ __html: BOOTSTRAP }} /></head>
    <body>{children}</body>
  </html>;
}

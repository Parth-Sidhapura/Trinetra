import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TRINETRA — Criminal Network Analysis",
  description: "SIH 2026 · PS 26189 · Ministry of Home Affairs / NCRB",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

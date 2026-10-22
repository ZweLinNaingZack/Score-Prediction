import type { Metadata } from "next";
import { Geist_Mono, Open_Sans } from "next/font/google";

import Header from "@/components/Header";
import "./globals.css";

// Segoe UI is the primary face (Windows). Open Sans is the close-looking fallback elsewhere.
const fallback = Open_Sans({
  variable: "--font-fallback",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Score Prediction",
  description: "Football score predictions from our own statistical model",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${fallback.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="relative flex min-h-dvh flex-col">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-accent focus:px-4 focus:py-2 focus:text-on-accent"
        >
          Skip to content
        </a>
        <div className="hero-glow pointer-events-none absolute inset-x-0 top-0 -z-10 h-[28rem]" />
        <Header />
        <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-5 py-12">
          {children}
        </main>
        <footer className="mx-auto w-full max-w-6xl px-5 py-10 text-xs text-muted">
          Predictions are for entertainment only.
        </footer>
      </body>
    </html>
  );
}

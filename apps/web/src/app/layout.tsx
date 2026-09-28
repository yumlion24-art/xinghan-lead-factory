import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppShell } from "@/components/app-shell";
import "./globals.css";


export const metadata: Metadata = {
  title: "Xinghan Lead Factory",
  description: "Local B2B account discovery and qualification workspace",
};


export default function RootLayout({ children }: { children: ReactNode }) {
  return <html lang="en"><body><AppShell>{children}</AppShell></body></html>;
}


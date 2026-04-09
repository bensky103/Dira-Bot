import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Dira-Bot Map",
  description: "Interactive apartment map for Dira-Bot",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="he" dir="ltr">
      <body>{children}</body>
    </html>
  );
}

import "./globals.css";
import type { Metadata } from "next";
import { Nav } from "@/components/nav";

export const metadata: Metadata = {
  title: "Warehouse Management System",
  description: "Build me a Warehouse Management System with products, warehouses, inventory levels, and inbound/outbound shipments.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-background text-foreground antialiased">
        <div className="flex min-h-screen">
          <Nav />
          <main className="flex-1 p-8">{children}</main>
        </div>
      </body>
    </html>
  );
}

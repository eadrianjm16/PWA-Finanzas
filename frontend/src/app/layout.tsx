import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import BottomNav from "@/components/BottomNav";
import ServiceWorkerRegister from "@/components/ServiceWorkerRegister";
import SWRProvider from "@/components/SWRProvider";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "Finanzas",
  description: "Saldo y movimientos de tus cuentas bancarias.",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "Finanzas",
  },
  icons: {
    icon: "/icons/icon.svg",
    apple: "/icons/icon.svg",
  },
};

export const viewport: Viewport = {
  themeColor: "#08080c",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="es" className={`h-full antialiased ${inter.variable}`}>
      <body className="min-h-full">
        <SWRProvider>
          <AuthProvider>
            {children}
            <BottomNav />
          </AuthProvider>
        </SWRProvider>
        <ServiceWorkerRegister />
      </body>
    </html>
  );
}

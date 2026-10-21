import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import SmoothScroll from "@/components/motion/SmoothScroll";
import { getSitio, getSlugsLegales, imagen } from "@/lib/contenido";
import { siteUrl } from "@/lib/supabase/env";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const dynamic = "force-dynamic";

export async function generateMetadata(): Promise<Metadata> {
  const sitio = await getSitio();
  const titulo = `${sitio.nombre} — ${sitio.lema}`;
  return {
    metadataBase: new URL(siteUrl()),
    title: { default: titulo, template: `%s · ${sitio.nombre}` },
    description: sitio.descripcion,
    applicationName: sitio.nombre,
    openGraph: {
      type: "website",
      locale: "es_CL",
      siteName: sitio.nombre,
      title: titulo,
      description: sitio.descripcion,
      images: sitio.imagenSocial ? [{ url: imagen(sitio.imagenSocial), alt: sitio.nombre }] : undefined,
    },
    twitter: { card: "summary_large_image" },
  };
}

export const viewport: Viewport = { themeColor: "#08090d", colorScheme: "dark" };

export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const [sitio, legales] = await Promise.all([getSitio(), getSlugsLegales()]);
  return (
    <html lang="es">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <SmoothScroll />
        <Nav />
        <main className="relative">{children}</main>
        <Footer sitio={sitio} legales={legales} />
      </body>
    </html>
  );
}

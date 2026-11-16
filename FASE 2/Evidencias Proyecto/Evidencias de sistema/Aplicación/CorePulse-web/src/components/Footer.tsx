import Link from "next/link";
import Logo from "./Logo";
import type { Sitio } from "@/lib/contenido";

export default function Footer({ sitio, legales }: { sitio: Sitio; legales: { slug: string; titulo: string }[] }) {
  const columns = [
    {
      title: "Producto",
      links: [
        { href: "/funciones", label: "Funciones" },
        { href: "/precios", label: "Precios" },
        { href: "/descargar", label: "Descargar" },
        { href: "/novedades", label: "Novedades" },
      ],
    },
    {
      title: "Cuenta",
      links: [
        { href: "/login", label: "Iniciar sesión" },
        { href: "/registro", label: "Crear cuenta" },
        { href: "/cuenta", label: "Mi cuenta" },
      ],
    },
    { title: "Legal", links: legales.map((l) => ({ href: `/legal/${l.slug}`, label: l.titulo })) },
  ];
  return (
    <footer className="relative border-t border-white/[0.06] px-6 pb-12 pt-16">
      <div className="mx-auto grid max-w-6xl gap-12 md:grid-cols-[1.4fr_repeat(3,1fr)]">
        <div>
          <div className="flex items-center gap-2">
            <Logo className="h-8 w-8" />
            <span className="font-semibold tracking-tight">
              Core<span className="text-accent">Pulse</span>
            </span>
          </div>
          <p className="mt-4 max-w-xs text-sm leading-relaxed text-muted">
            {sitio.descripcionCorta}
          </p>
          {sitio.emailSoporte && (
            <a href={`mailto:${sitio.emailSoporte}`} className="mt-3 inline-block text-sm text-accent hover:underline">
              {sitio.emailSoporte}
            </a>
          )}
        </div>
        {columns.map((col) => (
          <div key={col.title}>
            <h3 className="text-xs font-semibold uppercase tracking-[0.14em] text-muted">{col.title}</h3>
            <ul className="mt-4 space-y-2.5">
              {col.links.map((l) => (
                <li key={l.href}>
                  <Link href={l.href} className="text-sm text-ink/80 transition-colors hover:text-accent">
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="mx-auto mt-14 flex max-w-6xl flex-col justify-between gap-3 border-t border-white/[0.06] pt-6 text-xs text-muted sm:flex-row">
        <span>© {new Date().getFullYear()} {sitio.nombre}. Todos los derechos reservados.</span>
        <span>{sitio.avisoLegal}</span>
      </div>
    </footer>
  );
}

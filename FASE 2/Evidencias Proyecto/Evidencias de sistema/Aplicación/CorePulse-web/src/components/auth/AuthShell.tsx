import Logo from "@/components/Logo";
import { Reveal } from "@/components/motion/Reveal";

// Marco común de las páginas de cuenta: tarjeta de vidrio sobre aurora.
export default function AuthShell({ titulo, texto, children }: { titulo: string; texto?: string; children: React.ReactNode }) {
  return (
    <section className="relative flex min-h-[100svh] items-center justify-center overflow-hidden px-4 py-32">
      <div aria-hidden className="animate-aurora pointer-events-none absolute left-1/2 top-1/4 -z-10 h-[520px] w-[760px] -translate-x-1/2 rounded-full bg-[radial-gradient(closest-side,rgba(78,221,200,0.18),rgba(183,86,234,0.1)_60%,transparent)]" />
      <Reveal className="w-full max-w-md">
        <div className="rounded-3xl border border-white/10 bg-[#0e1118]/80 p-8 shadow-[0_40px_120px_-30px_rgba(0,0,0,0.9)] backdrop-blur-xl sm:p-10">
          <Logo className="h-11 w-11" />
          <h1 className="mt-6 text-3xl font-semibold tracking-[-0.03em]">{titulo}</h1>
          {texto && <p className="mt-2 text-muted">{texto}</p>}
          <div className="mt-8">{children}</div>
        </div>
      </Reveal>
    </section>
  );
}

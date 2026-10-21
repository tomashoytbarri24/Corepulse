import { Reveal, StaggerWords } from "@/components/motion/Reveal";

export default function PageHeader({ kicker, title, text }: { kicker: string; title: string; text?: string }) {
  return (
    <section className="relative overflow-hidden px-6 pb-16 pt-40 text-center md:pt-48">
      <div aria-hidden className="animate-aurora pointer-events-none absolute -top-32 left-1/2 -z-10 h-[480px] w-[760px] -translate-x-1/2 rounded-full bg-[radial-gradient(closest-side,rgba(78,221,200,0.16),rgba(183,86,234,0.08)_60%,transparent)]" />
      <Reveal>
        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-accent">{kicker}</p>
      </Reveal>
      <h1 className="mx-auto mt-5 max-w-4xl text-[clamp(2.4rem,6vw,4.75rem)] font-semibold leading-[1.02] tracking-[-0.045em]">
        <StaggerWords text={title} delay={0.1} />
      </h1>
      {text && (
        <Reveal delay={0.35}>
          <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-muted">{text}</p>
        </Reveal>
      )}
    </section>
  );
}

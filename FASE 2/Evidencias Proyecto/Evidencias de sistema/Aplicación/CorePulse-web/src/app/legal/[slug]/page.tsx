import type { Metadata } from "next";
import { notFound } from "next/navigation";
import PageHeader from "@/components/PageHeader";
import { Reveal } from "@/components/motion/Reveal";
import { getDocumentoLegal } from "@/lib/contenido";

export const dynamic = "force-dynamic";
export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const doc = await getDocumentoLegal(slug);
  return { title: doc?.titulo ?? "Legal" };
}

export default async function LegalPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const doc = await getDocumentoLegal(slug);
  if (!doc) notFound();
  return (
    <>
      <PageHeader kicker="Legal" title={doc.titulo} text={doc.actualizado} />
      <article className="mx-auto max-w-2xl space-y-12 px-6 pb-32">
        {doc.secciones.map((s, i) => (
          <Reveal key={s.titulo} delay={i * 0.04}>
            <h2 className="text-xl font-semibold tracking-tight">{s.titulo}</h2>
            <p className="mt-3 whitespace-pre-line leading-relaxed text-muted">{s.texto}</p>
          </Reveal>
        ))}
      </article>
    </>
  );
}

import Hero from "@/components/home/Hero";
import StickyFeatures from "@/components/home/StickyFeatures";
import ThemesGallery from "@/components/home/ThemesGallery";
import { Bento, FinalCta, Manifesto, Marquee, Stats } from "@/components/home/Sections";
import { getCifras, getDestacados, getFunciones, getInicio, getSitio, getTemas, imagen } from "@/lib/contenido";

export const dynamic = "force-dynamic";

export default async function Home() {
  const [inicio, sitio, funciones, cifras, destacados, temas] = await Promise.all([
    getInicio(),
    getSitio(),
    getFunciones(),
    getCifras(),
    getDestacados(),
    getTemas(),
  ]);
  const pasos = funciones
    .filter((f) => f.en_portada)
    .map((f) => ({
      kicker: f.etiqueta,
      title: f.titulo_portada ?? f.titulo,
      text: f.texto_portada ?? f.puntos.join(". "),
      image: imagen(f.imagen),
      color: f.color,
    }));

  return (
    <>
      <Hero inicio={inicio} sitio={sitio} imagenUrl={imagen(inicio.imagen)} />
      <Marquee items={inicio.marquesina ?? []} />
      <Manifesto text={inicio.manifiesto} />
      <StickyFeatures steps={pasos} />
      <Stats cifras={cifras} />
      <Bento items={destacados} titulo={inicio.destacadosTitulo} subtitulo={inicio.destacadosSubtitulo} />
      <ThemesGallery
        themes={temas.map((t) => ({ name: t.nombre, image: imagen(t.imagen), accent: t.color }))}
        etiqueta={inicio.temasEtiqueta}
        titulo={inicio.temasTitulo}
        subtitulo={inicio.temasSubtitulo}
      />
      <FinalCta titulo1={inicio.cierreTitulo1} titulo2={inicio.cierreTitulo2} texto={inicio.cierreTexto} />
    </>
  );
}

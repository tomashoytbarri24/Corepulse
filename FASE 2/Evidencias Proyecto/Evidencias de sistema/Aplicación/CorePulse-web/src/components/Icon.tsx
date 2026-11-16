// Íconos lineales propios (mismo trazo que los Glyph de la app).
const paths: Record<string, string> = {
  gamepad: "M7 9v4M5 11h4M15.5 10.5h.01M18 12.5h.01M6.5 6h11A4.5 4.5 0 0 1 22 10.5v1.6a3.9 3.9 0 0 1-7 2.4l-.6-.8H9.6l-.6.8a3.9 3.9 0 0 1-7-2.4v-1.6A4.5 4.5 0 0 1 6.5 6Z",
  thermo: "M14 14.8V5a2 2 0 1 0-4 0v9.8a4 4 0 1 0 4 0ZM12 9v7",
  wrench: "M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.6 2.6-2.4-.6-.6-2.4 2.6-2.6Z",
  bolt: "M13 2 4 14h7l-1 8 9-12h-7l1-8Z",
  lock: "M6 10h12v11H6zM8.5 10V7a3.5 3.5 0 1 1 7 0v3M12 14.5v3",
  check: "M5 12.5l4.5 4.5L19 7.5",
  dash: "M6 12h12",
  windows: "M3 5.5l7.5-1v7H3zM12.5 4.2 21 3v8.5h-8.5zM3 12.5h7.5v7L3 18.5zM12.5 12.5H21V21l-8.5-1.2z",
};

export default function Icon({ name, className }: { name: keyof typeof paths | string; className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden>
      <path d={paths[name]} />
    </svg>
  );
}

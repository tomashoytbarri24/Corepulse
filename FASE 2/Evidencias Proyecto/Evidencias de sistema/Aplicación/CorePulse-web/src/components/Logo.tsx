// Marca de CorePulse: la misma «C» del icono de bandeja de la app, con pulso.
export default function Logo({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" className={className} aria-hidden>
      <defs>
        <linearGradient id="cp-logo" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#4EDDC8" />
          <stop offset="0.55" stopColor="#17B9F7" />
          <stop offset="1" stopColor="#B756EA" />
        </linearGradient>
      </defs>
      <rect x="4" y="4" width="56" height="56" rx="16" fill="#12303A" stroke="url(#cp-logo)" strokeWidth="2.5" />
      <path d="M41 22.5a13 13 0 1 0 0 19" fill="none" stroke="#F3F7FF" strokeWidth="5" strokeLinecap="round" />
      <path d="M30 32h4l2.5-5 3 10 2.5-5h4" fill="none" stroke="url(#cp-logo)" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

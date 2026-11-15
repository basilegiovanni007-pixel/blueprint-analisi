// Indicatore di caricamento in stile blueprint: un compasso che traccia una circonferenza.
export default function Caricamento({ testo }: { testo: string }) {
  return (
    <div className="caricamento" role="status">
      <svg width="40" height="40" viewBox="0 0 40 40" aria-hidden="true">
        <circle cx="20" cy="20" r="16" className="caricamento-cerchio" />
        {/* Il braccio del compasso, che gira attorno al centro */}
        <g className="caricamento-braccio">
          <line x1="20" y1="20" x2="36" y2="20" />
          <circle cx="20" cy="20" r="2" fill="var(--bianco)" />
        </g>
      </svg>
      {testo}
    </div>
  );
}

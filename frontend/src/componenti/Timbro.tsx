// Il "timbro" di un traguardo: un cerchio con un simbolo, come il timbro di approvazione
// su una tavola tecnica. Spento (tratteggiato) finché il traguardo non è raggiunto.
type Props = {
  simbolo: string;
  ottenuto: boolean;
  grande?: boolean;
};

export default function Timbro({ simbolo, ottenuto, grande }: Props) {
  const lato = grande ? 76 : 58;
  // Più caratteri = scritta più piccola, così sta sempre dentro il cerchio
  const corpo = simbolo.length <= 2 ? 0.36 : simbolo.length <= 3 ? 0.28 : 0.22;
  return (
    <svg
      className={"timbro-traguardo" + (ottenuto ? " ottenuto" : "")}
      width={lato}
      height={lato}
      viewBox="0 0 100 100"
      aria-hidden="true"
    >
      <circle cx="50" cy="50" r="45" className="timbro-anello" />
      <circle cx="50" cy="50" r="37" className="timbro-anello-interno" />
      {/* Tacche come su un goniometro */}
      {Array.from({ length: 24 }, (_, i) => {
        const angolo = (i / 24) * 2 * Math.PI;
        return (
          <line
            key={i}
            x1={50 + 41 * Math.cos(angolo)}
            y1={50 + 41 * Math.sin(angolo)}
            x2={50 + 45 * Math.cos(angolo)}
            y2={50 + 45 * Math.sin(angolo)}
            className="timbro-tacca"
          />
        );
      })}
      <text x="50" y="50" dominantBaseline="central" textAnchor="middle" fontSize={100 * corpo} className="timbro-simbolo">
        {simbolo}
      </text>
    </svg>
  );
}

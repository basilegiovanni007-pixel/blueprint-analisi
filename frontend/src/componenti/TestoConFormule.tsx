// Mostra un testo che contiene formule in linea scritte tra simboli di dollaro.
// Esempio: "Poniamo $u = x^2$ e deriviamo" -> testo normale + formula KaTeX + testo normale.
import Formula from "./Formula";

export default function TestoConFormule({ testo }: { testo: string }) {
  // split("$") divide il testo: i pezzi in posizione dispari (1, 3, 5...) sono le formule
  const pezzi = testo.split("$");
  return (
    <>
      {pezzi.map((pezzo, i) => (i % 2 === 1 ? <Formula key={i} latex={pezzo} /> : <span key={i}>{pezzo}</span>))}
    </>
  );
}

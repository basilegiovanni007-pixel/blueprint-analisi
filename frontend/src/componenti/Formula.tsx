// Mostra una formula scritta in LaTeX usando la libreria KaTeX.
import katex from "katex";

type Props = {
  latex: string; // es. "\\frac{1}{x}"
  blocco?: boolean; // true = formula grande centrata, false = in linea col testo
};

export default function Formula({ latex, blocco = false }: Props) {
  // KaTeX trasforma il LaTeX in HTML. throwOnError:false evita che una formula
  // scritta male blocchi tutta la pagina: viene mostrata in rosso e basta.
  const html = katex.renderToString(latex, {
    displayMode: blocco,
    throwOnError: false,
  });

  return <span dangerouslySetInnerHTML={{ __html: html }} />;
}

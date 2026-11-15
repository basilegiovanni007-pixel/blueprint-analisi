// La fonte di un passaggio: una citazione cliccabile dal Magazzino (📎) oppure
// l'avviso che il concetto non è ancora negli appunti (⚠).
import { indirizzoFile, type Citazione } from "../api/client";

type Props = {
  concetto: string | null;
  citazione: Citazione | null;
  mancante: boolean;
};

export default function Fonte({ concetto, citazione, mancante }: Props) {
  if (citazione) {
    return (
      <details className="fonte">
        <summary>
          📎 {citazione.fonte}, {concetto}
          {citazione.pagina ? `, p. ${citazione.pagina}` : ""}
        </summary>
        <blockquote>{citazione.estratto}</blockquote>
        <a href={indirizzoFile(citazione.documento_id, citazione.pagina)} target="_blank" rel="noreferrer">
          Apri "{citazione.documento}"
        </a>
      </details>
    );
  }
  if (mancante) {
    return (
      <p className="fonte-mancante">
        ⚠ Questo passaggio richiede: <strong>{concetto}</strong>, che non è ancora nei tuoi appunti.
      </p>
    );
  }
  return null;
}

// Campo in cui lo studente scrive una funzione, con esempi pronti e messaggio d'errore.
import type { ReactNode } from "react";

type Props = {
  etichetta: string; // es. "f(x) ="
  valore: string;
  onCambia: (valore: string) => void;
  esempi?: string[];
  errore?: string;
  children?: ReactNode; // eventuali altri campi da mettere sulla stessa riga
};

export default function CampoFunzione({ etichetta, valore, onCambia, esempi = [], errore, children }: Props) {
  return (
    <div className="campo-funzione">
      <div className="campo-funzione-riga">
        <label className="campo campo-largo">
          <span>{etichetta}</span>
          <input value={valore} onChange={(e) => onCambia(e.target.value)} spellCheck={false} autoComplete="off" />
        </label>
        {children}
      </div>
      {esempi.length > 0 && (
        <div className="esempi esempi-compatti">
          <span className="nota">Prova con:</span>
          {esempi.map((esempio) => (
            <button key={esempio} className="esempio" onClick={() => onCambia(esempio)}>
              {esempio}
            </button>
          ))}
        </div>
      )}
      {errore && <p className="messaggio-errore">{errore}</p>}
    </div>
  );
}

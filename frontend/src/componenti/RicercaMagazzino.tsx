// Casella per cercare "per significato" tra i blocchi del Magazzino.
// È la stessa ricerca che userà il risolutore per trovare definizioni e teoremi.
import { useState, type FormEvent } from "react";

import { cercaNelMagazzino, indirizzoFile, type RisultatoRicerca } from "../api/client";

export default function RicercaMagazzino() {
  const [domanda, setDomanda] = useState("");
  const [risultati, setRisultati] = useState<RisultatoRicerca[] | null>(null); // null = nessuna ricerca fatta
  const [inCorso, setInCorso] = useState(false);
  const [errore, setErrore] = useState("");

  async function cerca(evento: FormEvent) {
    evento.preventDefault(); // evita che il browser ricarichi la pagina all'invio del modulo
    if (!domanda.trim()) return;
    setInCorso(true);
    setErrore("");
    try {
      setRisultati(await cercaNelMagazzino(domanda));
    } catch (e) {
      setErrore((e as Error).message);
      setRisultati(null);
    }
    setInCorso(false);
  }

  return (
    <div>
      <form className="riga-ricerca" onSubmit={cerca}>
        <input
          className="campo-ricerca"
          value={domanda}
          onChange={(e) => setDomanda(e.target.value)}
          placeholder="Es. come si risolve una forma indeterminata 0/0"
          aria-label="Cerca nel Magazzino"
        />
        <button className="bottone" disabled={inCorso || !domanda.trim()}>
          {inCorso ? "Cerco…" : "Cerca"}
        </button>
      </form>

      {errore && <p className="messaggio-errore">{errore}</p>}

      {risultati && risultati.length === 0 && (
        <p className="nota" style={{ marginTop: 14 }}>
          Nessun blocco trovato. Carica dei documenti o riattiva quelli disattivati.
        </p>
      )}

      {risultati && risultati.length > 0 && (
        <ol className="elenco-blocchi">
          {risultati.map((risultato) => (
            <li key={risultato.id} className="blocco">
              <div className="blocco-testa">
                <span className={"tipo tipo-" + risultato.tipo.replace(" ", "-")}>{risultato.tipo}</span>
                <a
                  className="nota"
                  href={indirizzoFile(risultato.documento.id, risultato.pagina)}
                  target="_blank"
                  rel="noreferrer"
                >
                  📎 {risultato.documento.fonte}, {risultato.documento.titolo}
                  {risultato.pagina ? `, p. ${risultato.pagina}` : ""}
                </a>
                <span className="nota somiglianza" title="Quanto il blocco è vicino alla tua ricerca">
                  {Math.round(risultato.somiglianza * 100)}%
                </span>
              </div>
              <p>{risultato.testo}</p>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

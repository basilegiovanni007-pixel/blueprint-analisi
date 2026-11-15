// "Hook" riutilizzabile: chiede dei dati al backend ogni volta che cambia ciò che lo studente
// ha scritto, ma aspetta un attimo che smetta di scrivere (per non fare una richiesta a ogni tasto).
import { useEffect, useState } from "react";

type Esito<T> = { dati: T | null; errore: string; inCorso: boolean };

/**
 * @param richiesta   funzione che chiama il backend
 * @param dipendenze  valori da cui dipende la richiesta: quando cambiano, si richiede di nuovo
 * @param attiva      false = non chiedere nulla (es. campo vuoto)
 */
export function useRichiesta<T>(richiesta: () => Promise<T>, dipendenze: unknown[], attiva = true): Esito<T> {
  const [esito, setEsito] = useState<Esito<T>>({ dati: null, errore: "", inCorso: false });

  useEffect(() => {
    if (!attiva) {
      setEsito({ dati: null, errore: "", inCorso: false });
      return;
    }
    let annullata = false; // diventa true se nel frattempo lo studente ha scritto altro
    setEsito((precedente) => ({ ...precedente, inCorso: true }));
    const attesa = window.setTimeout(() => {
      richiesta()
        .then((dati) => !annullata && setEsito({ dati, errore: "", inCorso: false }))
        .catch((e: Error) => !annullata && setEsito({ dati: null, errore: e.message, inCorso: false }));
    }, 350);
    return () => {
      annullata = true;
      window.clearTimeout(attesa);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...dipendenze, attiva]);

  return esito;
}

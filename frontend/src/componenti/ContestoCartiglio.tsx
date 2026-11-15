// Il "contesto" del cartiglio: permette a una pagina qualsiasi (es. la soluzione di un
// esercizio) di cambiare ciò che è scritto nel cartiglio in basso a destra.
import { createContext, useContext, useEffect, type ReactNode, useState } from "react";

export type DatiCartiglio = {
  titolo: string; // es. "Limite"
  esercizio?: string; // il testo dell'esercizio
  argomento: string; // es. "Limiti"
  data?: string; // in formato AAAA-MM-GG...; se manca, oggi
};

type Contesto = { dati: DatiCartiglio | null; imposta: (dati: DatiCartiglio | null) => void };

const ContestoCartiglio = createContext<Contesto>({ dati: null, imposta: () => {} });

export function FornitoreCartiglio({ children }: { children: ReactNode }) {
  const [dati, imposta] = useState<DatiCartiglio | null>(null);
  return <ContestoCartiglio.Provider value={{ dati, imposta }}>{children}</ContestoCartiglio.Provider>;
}

/** Legge i dati attuali del cartiglio (usato dal componente Cartiglio). */
export const useDatiCartiglio = () => useContext(ContestoCartiglio).dati;

/** Una pagina chiama questo hook per scrivere nel cartiglio; quando la pagina sparisce, il cartiglio torna normale. */
export function useCartiglio(dati: DatiCartiglio | null) {
  const { imposta } = useContext(ContestoCartiglio);
  const chiave = JSON.stringify(dati);
  useEffect(() => {
    imposta(dati);
    return () => imposta(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chiave]);
}

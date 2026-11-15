// Tutte le chiamate al backend passano da questo file.
// Così, se un giorno cambia un indirizzo, lo correggiamo in un posto solo.

import type { Elemento } from "../componenti/Grafico";

// ---------- funzione comune ----------

// Esegue una richiesta e, se qualcosa va storto, lancia un errore con un messaggio
// in italiano pronto da mostrare all'utente.
async function chiedi<T>(indirizzo: string, opzioni?: RequestInit): Promise<T> {
  let risposta: Response;
  try {
    risposta = await fetch(indirizzo, opzioni);
  } catch {
    throw new Error("Backend non raggiungibile: controlla che sia acceso.");
  }
  if (!risposta.ok) {
    // Il backend mette la spiegazione dell'errore nel campo "detail"
    let messaggio = `Errore ${risposta.status}`;
    try {
      const corpo = await risposta.json();
      if (typeof corpo.detail === "string") messaggio = corpo.detail;
    } catch {
      /* la risposta non era JSON: teniamo il messaggio generico */
    }
    throw new Error(messaggio);
  }
  // 204 = "fatto, nessun contenuto" (es. dopo un'eliminazione)
  if (risposta.status === 204) return undefined as T;
  return risposta.json();
}

const JSON_HEADERS = { "Content-Type": "application/json" };

// ---------- stato ----------

export type StatoBackend = {
  stato: string;
  versione_app: string;
  fase: number;
  versione_sympy: string;
  ricerca: { stato: "non caricato" | "in caricamento" | "pronto" | "errore"; errore: string | null };
  prova_calcolo: {
    funzione: string; // in LaTeX
    derivata: string; // in LaTeX
  };
};

export const leggiStato = () => chiedi<StatoBackend>("/api/stato");

// ---------- risolutore ----------

// Il riferimento a un blocco del Magazzino che giustifica un passaggio
export type Citazione = {
  blocco_id: number;
  documento_id: number;
  documento: string;
  fonte: string;
  pagina: number | null;
  tipo: string;
  estratto: string;
};

export type Passaggio = {
  numero: number;
  titolo: string;
  testo: string; // spiegazione; le formule in linea stanno tra $...$
  formula: string | null; // LaTeX
  concetto: string | null; // nome del teorema/regola usato
  citazione: Citazione | null;
  mancante: boolean; // true = il concetto non è nel Magazzino
  domanda: string | null; // domanda di "Mettimi alla prova" (null = passaggio senza domanda)
};

export type Soluzione = {
  id: number; // posizione nello Storico
  documento_id: number | null; // se è stato aggiunto al Magazzino
  risolto_il: string;
  problema: { tipo: string; descrizione: string; latex: string; argomento: string };
  // Che tipo di risposta finale chiede "Mettimi alla prova" (null = non controllabile)
  controllo_finale: { tipo: "espressione" | "scelta" | "vettore" | "edo"; domanda: string } | null;
  risultato_latex: string;
  risposta_latex: string;
  verificato: boolean;
  passaggi_verificati: boolean;
  metodo: string;
  passaggi: Passaggio[];
  concetti_mancanti: string[];
  avvisi: string[];
  grafico: DatiGrafico | null;
};

// Grafico di una funzione di una variabile (limiti, derivate, integrali)
export type DatiFunzione = {
  tipo: "funzione";
  funzione: string; // formula calcolabile dal browser
  variabile: string;
  derivata: string | null;
  punto: number | null;
  area: [number, number] | null;
  // Altre curve da disegnare in secondo piano: per le equazioni differenziali sono
  // alcune soluzioni della famiglia, ottenute cambiando il valore delle costanti
  altre?: string[];
};

// Un punto notevole di una superficie: massimo, minimo, sella...
export type PuntoSuperficie = { x: number; y: number; z: number; tipo: string };

// Grafico di una funzione di due variabili (Analisi II)
export type DatiSuperficie = {
  tipo: "superficie";
  funzione: string;
  variabili: [string, string];
  finestra: { xmin: number; xmax: number; ymin: number; ymax: number };
  punti: PuntoSuperficie[];
  vincolo: string | null; // la curva g(x, y) = 0 dei massimi e minimi vincolati
  // Dominio di un integrale doppio: la variabile esterna va da a a b, quella interna
  // dal bordo inferiore a quello superiore (che possono dipendere dalla variabile esterna)
  dominio: { esterna: string; a: number; b: number; inferiore: string; superiore: string } | null;
};

export type DatiGrafico = DatiFunzione | DatiSuperficie;

export type EsercizioDaFile = { numero: number; testo: string };

export async function risolvi(testo: string, tipo: string) {
  const soluzione = await chiedi<Soluzione>("/api/risolutore/risolvi", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ testo, tipo }),
  });
  void aggiornaProgressi(); // un esercizio risolto può far scattare un traguardo
  return soluzione;
}

export function leggiEserciziDaFile(file: File) {
  const pacco = new FormData();
  pacco.append("file", file);
  return chiedi<{ nome_file: string; esercizi: EsercizioDaFile[] }>("/api/risolutore/da-file", {
    method: "POST",
    body: pacco,
  });
}

// ---------- storico ----------

// Un esercizio nell'elenco dello Storico
export type VoceStorico = {
  id: number;
  testo: string;
  tipo: string;
  tipo_richiesto: string;
  descrizione: string;
  argomento: string;
  problema_latex: string;
  risposta_latex: string;
  documento_id: number | null;
  risolto_il: string;
};

// Un esercizio dello Storico con la soluzione completa
export type EsercizioSalvato = Soluzione & VoceStorico;

export type EsitoRisposta = { corretto: boolean; messaggio: string };

export const elencaStorico = () => chiedi<VoceStorico[]>("/api/storico");

export const leggiEsercizio = (id: number) => chiedi<EsercizioSalvato>(`/api/storico/${id}`);

export const eliminaEsercizio = (id: number) => chiedi<void>(`/api/storico/${id}`, { method: "DELETE" });

// passaggio: indice del passaggio (da 0); null = risposta finale
export async function controllaRisposta(id: number, passaggio: number | null, risposta: string) {
  const esito = await chiedi<EsitoRisposta>(`/api/storico/${id}/controlla`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ passaggio, risposta }),
  });
  if (esito.corretto) void aggiornaProgressi(); // le risposte giuste contano per i traguardi
  return esito;
}

// ---------- progressi e traguardi ----------

export type Traguardo = {
  chiave: string;
  titolo: string;
  descrizione: string;
  simbolo: string;
  attuale: number;
  obiettivo: number;
  ottenuto: boolean;
  ottenuto_il: string | null;
};

export type Progressi = {
  oggi: string;
  serie: { attuale: number; record: number; studiato_oggi: boolean };
  totali: { esercizi: number; risposte_giuste: number; fatti_da_te: number; giorni_di_studio: number };
  per_argomento: { argomento: string; corso: string; esercizi: number }[];
  calendario: { giorno: string; attivita: number }[];
  traguardi: Traguardo[];
  nuovi: Traguardo[]; // traguardi appena raggiunti: l'app li festeggia
};

export const EVENTO_PROGRESSI = "blueprint:progressi";

export const leggiProgressi = () => chiedi<Progressi>("/api/progressi");

/**
 * Chiede i progressi aggiornati e li "annuncia" a tutta l'app con un evento del browser:
 * la barra laterale aggiorna la serie di giorni, e i traguardi nuovi compaiono come notifica.
 */
export async function aggiornaProgressi(): Promise<Progressi | null> {
  try {
    const progressi = await leggiProgressi();
    window.dispatchEvent(new CustomEvent<Progressi>(EVENTO_PROGRESSI, { detail: progressi }));
    return progressi;
  } catch {
    return null; // i progressi sono un "di più": se non arrivano, l'app funziona lo stesso
  }
}

export const aggiungiAlMagazzino = (id: number) =>
  chiedi<Documento>(`/api/storico/${id}/magazzino`, { method: "POST" });

// ---------- grafici ----------

const inviaJson = <T>(indirizzo: string, corpo: unknown) =>
  chiedi<T>(indirizzo, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corpo) });

// Una funzione pronta per essere disegnata
export type FunzionePronta = {
  latex: string;
  js: string; // formula calcolabile dal browser
  variabile: string;
  parametri: string[]; // le altre lettere, es. a e b in a*sin(b*x)
};

// Una tappa dello studio di funzione, con gli elementi da far comparire sul grafico
export type Tappa = {
  titolo: string;
  testo: string;
  formule: string[];
  elementi: Elemento[];
  concetto: string | null;
  citazione: Citazione | null;
  mancante: boolean;
};

export type StudioFunzione = {
  funzione: { latex: string; js: string; variabile: string };
  finestra: { xmin: number; xmax: number };
  tappe: Tappa[];
};

export type PolinomiTaylor = {
  funzione: { latex: string; js: string; variabile: string };
  centro: number;
  centro_latex: string;
  polinomi: { ordine: number; latex: string; js: string }[];
};

export type SerieNumerica = {
  termine: { latex: string; js: string; variabile: string };
  inizio: number;
  serie_latex: string;
  converge: boolean | null; // null = SymPy non è riuscito a stabilirlo
  somma_latex: string | null;
  somma: number | null;
};

export type SuperficiePronta = {
  latex: string;
  js: string;
  gradiente_latex: string;
  finestra: DatiSuperficie["finestra"];
  punti: PuntoSuperficie[];
};

export const preparaSuperficie = (testo: string) => inviaJson<SuperficiePronta>("/api/grafici/superficie", { testo });

export const preparaFunzione = (testo: string) => inviaJson<FunzionePronta>("/api/grafici/funzione", { testo });

export const studiaFunzione = (testo: string) => inviaJson<StudioFunzione>("/api/grafici/studio", { testo });

export const polinomiTaylor = (testo: string, centro: string, ordine_massimo: number) =>
  inviaJson<PolinomiTaylor>("/api/grafici/taylor", { testo, centro, ordine_massimo });

export const preparaSerie = (testo: string, inizio: number) =>
  inviaJson<SerieNumerica>("/api/grafici/serie", { testo, inizio });

// ---------- magazzino ----------

export type Opzioni = {
  argomenti: Record<string, string[]>; // corso -> elenco argomenti
  fonti: string[];
  tipi_blocco: string[];
  estensioni: string[];
};

export type Documento = {
  id: number;
  titolo: string;
  nome_file: string;
  argomento: string;
  corso: string;
  fonte: string;
  data: string;
  attivo: boolean;
  caricato_il: string;
  numero_blocchi: number;
  blocchi_per_tipo: Record<string, number>;
};

export type Blocco = {
  id: number;
  ordine: number;
  pagina: number | null;
  testo: string;
  tipo: string;
};

export type DocumentoConBlocchi = Documento & { blocchi: Blocco[] };

export type RisultatoRicerca = Blocco & {
  somiglianza: number;
  documento: { id: number; titolo: string; fonte: string; argomento: string };
};

export type VoceMappa = {
  argomento: string;
  documenti: number;
  blocchi: number;
  blocchi_per_tipo: Record<string, number>;
  tipi_mancanti: string[];
  copertura: number; // da 0 a 1
};

export type Mappa = { corso: string; argomenti: VoceMappa[] }[];

export type Etichette = { titolo?: string; argomento: string; fonte: string; data: string };

export const leggiOpzioni = () => chiedi<Opzioni>("/api/magazzino/opzioni");

export const elencaDocumenti = () => chiedi<Documento[]>("/api/magazzino/documenti");

export const leggiDocumento = (id: number) => chiedi<DocumentoConBlocchi>(`/api/magazzino/documenti/${id}`);

export function caricaDocumento(file: File, etichette: Etichette) {
  // FormData è il "pacco" con cui si spedisce un file insieme ad altri campi
  const pacco = new FormData();
  pacco.append("file", file);
  pacco.append("argomento", etichette.argomento);
  pacco.append("fonte", etichette.fonte);
  pacco.append("data", etichette.data);
  if (etichette.titolo) pacco.append("titolo", etichette.titolo);
  return chiedi<Documento>("/api/magazzino/documenti", { method: "POST", body: pacco });
}

export const modificaDocumento = (id: number, modifica: Partial<Etichette & { attivo: boolean }>) =>
  chiedi<Documento>(`/api/magazzino/documenti/${id}`, {
    method: "PATCH",
    headers: JSON_HEADERS,
    body: JSON.stringify(modifica),
  });

export const eliminaDocumento = (id: number) =>
  chiedi<void>(`/api/magazzino/documenti/${id}`, { method: "DELETE" });

export const modificaBlocco = (id: number, modifica: { tipo?: string; testo?: string }) =>
  chiedi<Blocco>(`/api/magazzino/blocchi/${id}`, {
    method: "PATCH",
    headers: JSON_HEADERS,
    body: JSON.stringify(modifica),
  });

export const cercaNelMagazzino = (domanda: string) =>
  chiedi<RisultatoRicerca[]>(`/api/magazzino/cerca?q=${encodeURIComponent(domanda)}`);

export const leggiMappa = () => chiedi<Mappa>("/api/magazzino/mappa");

// Indirizzo del file originale; per i PDF si può aprire direttamente alla pagina giusta
export const indirizzoFile = (id: number, pagina?: number | null) =>
  `/api/magazzino/documenti/${id}/file` + (pagina ? `#page=${pagina}` : "");

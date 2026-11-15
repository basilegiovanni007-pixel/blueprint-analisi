// Mostra la soluzione di un esercizio in una delle quattro modalità di studio:
// - Soluzione completa: tutti i passaggi visibili;
// - Un passo alla volta: lo studente rivela i passaggi uno per uno;
// - Suggerimento: solo un indizio sul prossimo passo (titolo, concetto, fonte), senza la soluzione;
// - Mettimi alla prova: lo studente risponde alle domande dei passaggi e l'app gli dice se ha ragione.
// Sotto ci sono il risultato verificato, il grafico e le azioni (PDF, Magazzino).
import { useMemo, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";

import {
  aggiungiAlMagazzino,
  controllaRisposta,
  type DatiFunzione,
  type Passaggio,
  type Soluzione,
} from "../api/client";
import { compila } from "../grafici/calcolo";
import { useCartiglio } from "./ContestoCartiglio";
import Domanda, { Bollino } from "./Domanda";
import Fonte from "./Fonte";
import Formula from "./Formula";
import Grafico, { type Curva, type Elemento, type Finestra } from "./Grafico";
import Pannello from "./Pannello";
import TestoConFormule from "./TestoConFormule";
import VistaSuperficie from "./VistaSuperficie";

type Modo = "completa" | "passo" | "suggerimento" | "prova";

const MODI: { valore: Modo; nome: string; descrizione: string }[] = [
  { valore: "completa", nome: "Soluzione completa", descrizione: "Tutti i passaggi, subito." },
  { valore: "passo", nome: "Un passo alla volta", descrizione: "Riveli tu un passaggio dopo l'altro." },
  { valore: "suggerimento", nome: "Suggerimento", descrizione: "Solo un indizio sul prossimo passo, senza calcoli." },
  { valore: "prova", nome: "Mettimi alla prova", descrizione: "Rispondi tu: l'app ti dice se è corretto." },
];

// La modalità scelta viene ricordata dal browser (se possibile) per la prossima volta
const CHIAVE_MODO = "blueprint-modo-studio";
function modoSalvato(): Modo {
  try {
    const valore = localStorage.getItem(CHIAVE_MODO);
    return MODI.some((m) => m.valore === valore) ? (valore as Modo) : "completa";
  } catch {
    return "completa";
  }
}

// ---------- grafico dell'esercizio ----------

// Il punto del limite, la derivata accanto alla funzione, l'area dell'integrale,
// la famiglia di soluzioni di un'equazione differenziale.
function GraficoEsercizio({ dati }: { dati: DatiFunzione }) {
  const preparato = useMemo(() => {
    const curve: Curva[] = [{ id: "f", f: compila(dati.funzione, dati.variabile), disegna: true }];
    const elementi: Elemento[] = [];
    let finestra: Finestra = { xmin: -8, xmax: 8 };
    let legenda = "";

    if (dati.altre && dati.altre.length > 0) {
      dati.altre.forEach((formula, i) => curve.push({ id: "altra" + i, f: compila(formula, dati.variabile), stile: "tenue" }));
      legenda = "Ogni curva è una soluzione: si ottengono cambiando il valore delle costanti.";
      finestra = { xmin: -5, xmax: 5 };
    }
    if (dati.derivata) {
      curve.push({ id: "d", f: compila(dati.derivata, dati.variabile), stile: "seconda" });
      legenda = "Linea piena: la funzione. Linea tratteggiata: la sua derivata.";
    }
    if (dati.punto !== null) {
      elementi.push({ tipo: "verticale", x: dati.punto, etichetta: `${dati.variabile} → ${String(dati.punto).replace(".", ",")}` });
      finestra = { xmin: dati.punto - 6, xmax: dati.punto + 6 };
      legenda = "La linea tratteggiata indica il punto a cui tende la variabile.";
    }
    if (dati.area) {
      const [a, b] = dati.area;
      const margine = Math.max(1, (b - a) * 0.4);
      elementi.push({ tipo: "area", da: a, a: b });
      finestra = { xmin: a - margine, xmax: b + margine };
      legenda = "La zona colorata è l'area calcolata dall'integrale.";
    }
    return { curve, elementi, finestra, legenda };
  }, [dati]);

  return (
    <Pannello titolo="Grafico" largo>
      <Grafico
        chiave={dati.funzione + dati.derivata}
        curve={preparato.curve}
        elementi={preparato.elementi}
        finestra={preparato.finestra}
        descrizione="Grafico della funzione dell'esercizio"
      />
      <p className="nota">
        {preparato.legenda} <span className="non-stampare">Trascina per spostarti · Ctrl + rotella per lo zoom · doppio clic per tornare all'inizio</span>
      </p>
    </Pannello>
  );
}

// ---------- un passaggio ----------

function PassaggioCompleto({ passaggio, ritardo = 0, children }: { passaggio: Passaggio; ritardo?: number; children?: ReactNode }) {
  return (
    <motion.li
      className="passaggio"
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: ritardo, duration: 0.3 }}
    >
      <span className="passaggio-numero">{String(passaggio.numero).padStart(2, "0")}</span>
      <div className="passaggio-corpo">
        <h3>{passaggio.titolo}</h3>
        <p>
          <TestoConFormule testo={passaggio.testo} />
        </p>
        {passaggio.formula && (
          <div className="formula-scorrevole">
            <Formula blocco latex={passaggio.formula} />
          </div>
        )}
        <Fonte concetto={passaggio.concetto} citazione={passaggio.citazione} mancante={passaggio.mancante} />
        {children}
      </div>
    </motion.li>
  );
}

// ---------- svolgimento nelle quattro modalità ----------

type Props = { soluzione: Soluzione; modo: Modo; onCambiaModo: (modo: Modo) => void };

function Svolgimento({ soluzione, modo, onCambiaModo }: Props) {
  const passaggi = soluzione.passaggi;
  const totale = passaggi.length;

  // Quanti passaggi sono già visibili (in "completa" tutti)
  const [visibili, setVisibili] = useState(modo === "completa" ? totale : modo === "prova" ? 0 : Math.min(1, totale));
  // "Mettimi alla prova": esito di ogni passaggio e della risposta finale
  const [esiti, setEsiti] = useState<Record<number, { corretto: boolean; messaggio: string }>>({});
  const [finale, setFinale] = useState<{ corretto: boolean; messaggio: string } | null>(null);

  const finiti = visibili >= totale;
  const domande = passaggi.filter((p) => p.domanda).length;
  const giuste = Object.values(esiti).filter((e) => e.corretto).length + (finale?.corretto ? 1 : 0);

  // In "prova", se l'ultimo passaggio era già la risposta finale ed è stato indovinato, non la richiediamo
  const ultimo = passaggi[totale - 1];
  const ultimoIndovinato = Boolean(ultimo?.domanda && esiti[totale - 1]?.corretto);
  const chiediFinale = modo === "prova" && finiti && soluzione.controllo_finale !== null && !ultimoIndovinato && finale === null;

  let risultatoVisibile = false;
  if (modo === "completa") risultatoVisibile = true;
  if (modo === "passo") risultatoVisibile = finiti;
  if (modo === "prova") risultatoVisibile = finiti && !chiediFinale;

  function avanza(indice: number, esito?: { corretto: boolean; messaggio: string }) {
    if (esito) setEsiti((attuali) => ({ ...attuali, [indice]: esito }));
    setVisibili(indice + 1);
  }

  return (
    <>
      {totale > 0 && (
        <Pannello titolo={`Svolgimento · ${modo === "suggerimento" ? "suggerimenti" : soluzione.metodo}`} largo>
          {/* ----- Suggerimento: solo titolo, concetto e fonte dei prossimi passi ----- */}
          {modo === "suggerimento" ? (
            <>
              <ol className="suggerimenti">
                {passaggi.slice(0, visibili).map((passaggio, i) => (
                  <motion.li key={i} className="suggerimento" initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }}>
                    <span className="passaggio-numero">{String(i + 1).padStart(2, "0")}</span>
                    <div className="passaggio-corpo">
                      <p>
                        {i === 0 ? "Per cominciare: " : "Poi: "}
                        <strong>{passaggio.titolo.toLowerCase()}</strong>
                        {passaggio.concetto && <> — ti serve: {passaggio.concetto}</>}.
                      </p>
                      <Fonte concetto={passaggio.concetto} citazione={passaggio.citazione} mancante={passaggio.mancante} />
                    </div>
                  </motion.li>
                ))}
              </ol>
              <div className="riga-azioni">
                {!finiti && (
                  <button className="bottone-contorno" onClick={() => setVisibili(visibili + 1)}>
                    Un altro suggerimento ({visibili} di {totale})
                  </button>
                )}
                <button className="bottone-testo" onClick={() => onCambiaModo("completa")}>
                  Mostra la soluzione completa
                </button>
              </div>
            </>
          ) : (
            <>
              <ol className="passaggi">
                {passaggi.slice(0, visibili).map((passaggio, i) => (
                  <PassaggioCompleto key={i} passaggio={passaggio} ritardo={modo === "completa" ? 0.12 * i : 0}>
                    {modo === "prova" && esiti[i]?.corretto && <Bollino messaggio={esiti[i].messaggio} />}
                  </PassaggioCompleto>
                ))}

                {/* ----- Mettimi alla prova: il passaggio corrente, ancora nascosto ----- */}
                {modo === "prova" && !finiti && (
                  <li className="passaggio passaggio-corrente">
                    <span className="passaggio-numero">{String(visibili + 1).padStart(2, "0")}</span>
                    <div className="passaggio-corpo">
                      <h3>{passaggi[visibili].titolo}</h3>
                      {passaggi[visibili].domanda ? (
                        <Domanda
                          key={visibili}
                          domanda={passaggi[visibili].domanda!}
                          controlla={(risposta) => controllaRisposta(soluzione.id, visibili, risposta)}
                          onCorretta={(messaggio) => avanza(visibili, { corretto: true, messaggio })}
                          onRivela={() => avanza(visibili)}
                        />
                      ) : (
                        <div className="riga-azioni">
                          <span className="nota">Questo passaggio applica una regola: leggilo e prosegui.</span>
                          <button className="bottone-contorno" onClick={() => avanza(visibili)}>
                            Mostra il passaggio
                          </button>
                        </div>
                      )}
                    </div>
                  </li>
                )}
              </ol>

              {/* ----- Un passo alla volta ----- */}
              {modo === "passo" && !finiti && (
                <div className="riga-azioni">
                  <button className="bottone-contorno" onClick={() => setVisibili(visibili + 1)}>
                    Mostra il passo successivo ({visibili} di {totale})
                  </button>
                  <button className="bottone-testo" onClick={() => setVisibili(totale)}>
                    Mostra tutto
                  </button>
                </div>
              )}
            </>
          )}
        </Pannello>
      )}

      {/* ----- Mettimi alla prova: la risposta finale ----- */}
      {chiediFinale && soluzione.controllo_finale && (
        <Pannello titolo="La tua risposta finale" largo>
          <Domanda
            domanda={soluzione.controllo_finale.domanda}
            scelta={soluzione.controllo_finale.tipo === "scelta"}
            controlla={(risposta) => controllaRisposta(soluzione.id, null, risposta)}
            onCorretta={(messaggio) => setFinale({ corretto: true, messaggio })}
            onRivela={() => setFinale({ corretto: false, messaggio: "" })}
            testoRivela="Mostra il risultato"
          />
        </Pannello>
      )}

      {/* ----- Risultato ----- */}
      <AnimatePresence>
        {risultatoVisibile && (
          <motion.div
            className="pannello-largo"
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: modo === "completa" ? 0.12 * totale + 0.1 : 0.1 }}
          >
            <Pannello titolo="Risultato" classe={modo === "prova" && giuste > 0 ? "risultato-festa" : undefined}>
              <div className="risultato">
                <div className="formula-scorrevole">
                  <Formula blocco latex={soluzione.risposta_latex} />
                </div>
                {/* Il timbro compare solo se il controllo indipendente è stato fatto davvero */}
                {soluzione.verificato && <span className="timbro">✓ Verificato con SymPy</span>}
              </div>
              {modo === "prova" && (domande > 0 || finale !== null || ultimoIndovinato) && (
                <p className="punteggio">
                  {finale?.corretto && <Bollino messaggio={finale.messaggio} />}
                  Risposte giuste: <strong>{giuste}</strong> su {domande + (soluzione.controllo_finale && !ultimoIndovinato ? 1 : 0)}
                  {giuste > 0 && giuste === domande + (soluzione.controllo_finale && !ultimoIndovinato ? 1 : 0) && " · tutto giusto, complimenti!"}
                </p>
              )}
              {soluzione.concetti_mancanti.length > 0 && (
                <p className="nota" style={{ marginTop: 14 }}>
                  Concetti usati che mancano dal Magazzino: {soluzione.concetti_mancanti.join(" · ")}.{" "}
                  <Link to="/magazzino">Carica gli appunti</Link> che ne parlano per vedere le citazioni.
                </p>
              )}
            </Pannello>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Il grafico arriva insieme al risultato (in "completa" subito) */}
      {risultatoVisibile && soluzione.grafico?.tipo === "funzione" && <GraficoEsercizio dati={soluzione.grafico} />}
      {risultatoVisibile && soluzione.grafico?.tipo === "superficie" && (
        <Pannello titolo="Superficie e curve di livello" largo>
          <VistaSuperficie dati={soluzione.grafico} />
        </Pannello>
      )}
    </>
  );
}

// ---------- azioni: PDF e Magazzino ----------

function Azioni({ soluzione, testo, onPrimaDiStampare }: { soluzione: Soluzione; testo: string; onPrimaDiStampare: () => void }) {
  const [documento, setDocumento] = useState<number | null>(soluzione.documento_id);
  const [messaggio, setMessaggio] = useState("");
  const [inCorso, setInCorso] = useState(false);

  async function aggiungi() {
    setInCorso(true);
    try {
      const nuovo = await aggiungiAlMagazzino(soluzione.id);
      setDocumento(nuovo.id);
      setMessaggio(`Aggiunto al Magazzino come esercizio svolto (${nuovo.argomento}).`);
    } catch (e) {
      setMessaggio((e as Error).message);
    }
    setInCorso(false);
  }

  function esporta() {
    // Per il PDF serve la soluzione completa: passiamo a quella modalità e aspettiamo
    // che sia disegnata, poi apriamo la finestra di stampa del browser.
    onPrimaDiStampare();
    window.setTimeout(() => {
      const titolo = document.title;
      document.title = `Blueprint – ${testo.slice(0, 60)}`; // diventa il nome proposto per il file PDF
      window.print();
      document.title = titolo;
    }, 700);
  }

  return (
    <div className="azioni-soluzione">
      <button className="bottone-contorno" onClick={esporta}>
        ⤓ Esporta in PDF
      </button>
      {documento === null ? (
        <button className="bottone-contorno" onClick={aggiungi} disabled={inCorso}>
          + Aggiungi al Magazzino
        </button>
      ) : (
        <Link className="bottone-contorno" to="/magazzino">
          ✓ Nel Magazzino
        </Link>
      )}
      {messaggio && <span className="nota">{messaggio}</span>}
    </div>
  );
}

// ---------- la vista completa ----------

export default function VistaSoluzione({ soluzione, testo }: { soluzione: Soluzione; testo: string }) {
  const [modo, setModo] = useState<Modo>(modoSalvato);

  function cambiaModo(nuovo: Modo) {
    setModo(nuovo);
    try {
      localStorage.setItem(CHIAVE_MODO, nuovo);
    } catch {
      /* il browser non permette di salvare: pazienza, vale solo per questa volta */
    }
  }

  // Il cartiglio in basso a destra mostra l'esercizio, il suo argomento e la data
  useCartiglio({
    titolo: soluzione.problema.descrizione,
    esercizio: testo,
    argomento: soluzione.problema.argomento,
    data: soluzione.risolto_il,
  });

  return (
    <>
      {/* Intestazione visibile solo nel PDF */}
      <header className="solo-stampa intestazione-stampa pannello-largo">
        <small>BLUEPRINT · {soluzione.problema.descrizione} · {soluzione.problema.argomento}</small>
        <h1>{testo}</h1>
      </header>

      <Pannello titolo={`${soluzione.problema.descrizione} · ho capito così`} largo>
        <div className="formula-scorrevole">
          <Formula blocco latex={soluzione.problema.latex} />
        </div>
        <p className="nota non-stampare">Se non è l'esercizio che intendevi, correggi il testo e riprova.</p>
      </Pannello>

      {soluzione.avvisi.map((avviso) => (
        <p key={avviso} className="messaggio-avviso pannello-largo">
          {avviso}
        </p>
      ))}

      <Pannello titolo="Come vuoi studiarlo?" largo classe="non-stampare">
        <div className="modi-studio" role="tablist" aria-label="Modalità di studio">
          {MODI.map((m) => (
            <button
              key={m.valore}
              role="tab"
              aria-selected={modo === m.valore}
              className={"scheda-strumento" + (modo === m.valore ? " attiva" : "")}
              onClick={() => cambiaModo(m.valore)}
              title={m.descrizione}
            >
              {m.nome}
            </button>
          ))}
        </div>
        <p className="nota">{MODI.find((m) => m.valore === modo)!.descrizione}</p>
        <Azioni soluzione={soluzione} testo={testo} onPrimaDiStampare={() => cambiaModo("completa")} />
      </Pannello>

      {/* key: cambiando modalità (o esercizio) lo svolgimento riparte da capo */}
      <Svolgimento key={`${soluzione.id}-${soluzione.risolto_il}-${modo}`} soluzione={soluzione} modo={modo} onCambiaModo={cambiaModo} />
    </>
  );
}

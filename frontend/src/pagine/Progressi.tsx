// Pagina Progressi: giorni di studio consecutivi, calendario delle ultime settimane,
// esercizi per argomento e traguardi.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";

import { EVENTO_PROGRESSI, aggiornaProgressi, type Progressi as DatiProgressi } from "../api/client";
import Caricamento from "../componenti/Caricamento";
import Intestazione from "../componenti/Intestazione";
import Pannello from "../componenti/Pannello";
import Timbro from "../componenti/Timbro";

// ---------- calendario ----------

const LATO = 13; // lato di un quadratino, in pixel del disegno
const SPAZIO = 3;
const GIORNI_SETTIMANA = ["L", "M", "M", "G", "V", "S", "D"];

// Calendario a quadretti: una colonna per settimana, una riga per giorno (lunedì in alto).
// Più attività in un giorno = quadratino più pieno.
function Calendario({ giorni }: { giorni: DatiProgressi["calendario"] }) {
  // Il primo giorno può essere qualsiasi giorno della settimana: calcoliamo la riga di partenza
  const primo = new Date(giorni[0].giorno);
  const sfasamento = (primo.getDay() + 6) % 7; // 0 = lunedì
  const massimo = Math.max(1, ...giorni.map((g) => g.attivita));
  const colonne = Math.ceil((giorni.length + sfasamento) / 7);
  const larghezza = 18 + colonne * (LATO + SPAZIO);
  const altezza = 7 * (LATO + SPAZIO) + 16;

  return (
    <svg viewBox={`0 0 ${larghezza} ${altezza}`} className="calendario" role="img" aria-label="Calendario dei giorni di studio">
      {GIORNI_SETTIMANA.map((g, i) =>
        i % 2 === 0 ? (
          <text key={i} x={0} y={i * (LATO + SPAZIO) + LATO - 2} className="calendario-etichetta">
            {g}
          </text>
        ) : null,
      )}
      {giorni.map((g, i) => {
        const posizione = i + sfasamento;
        const colonna = Math.floor(posizione / 7);
        const riga = posizione % 7;
        const intensita = g.attivita === 0 ? 0 : 0.25 + 0.75 * (g.attivita / massimo);
        const data = new Date(g.giorno).toLocaleDateString("it-IT", { day: "numeric", month: "long" });
        return (
          <rect
            key={g.giorno}
            x={18 + colonna * (LATO + SPAZIO)}
            y={riga * (LATO + SPAZIO)}
            width={LATO}
            height={LATO}
            className={"calendario-giorno" + (i === giorni.length - 1 ? " oggi" : "")}
            style={{ fillOpacity: intensita }}
          >
            <title>{`${data}: ${g.attivita === 0 ? "nessuna attività" : g.attivita + (g.attivita === 1 ? " attività" : " attività")}`}</title>
          </rect>
        );
      })}
      <text x={18} y={altezza - 2} className="calendario-etichetta">
        {new Date(giorni[0].giorno).toLocaleDateString("it-IT", { day: "numeric", month: "short" })}
      </text>
      <text x={larghezza} y={altezza - 2} textAnchor="end" className="calendario-etichetta">
        oggi
      </text>
    </svg>
  );
}

// ---------- pagina ----------

export default function Progressi() {
  const [dati, setDati] = useState<DatiProgressi | null>(null);
  const [errore, setErrore] = useState("");

  useEffect(() => {
    // I dati arrivano dall'evento globale (così anche la barra laterale e le notifiche si aggiornano)
    const ascolta = (evento: Event) => setDati((evento as CustomEvent<DatiProgressi>).detail);
    window.addEventListener(EVENTO_PROGRESSI, ascolta);
    aggiornaProgressi().then((p) => p === null && setErrore("Non riesco a leggere i progressi: il backend è acceso?"));
    return () => window.removeEventListener(EVENTO_PROGRESSI, ascolta);
  }, []);

  const ottenuti = dati?.traguardi.filter((t) => t.ottenuto).length ?? 0;
  // Prima i traguardi raggiunti, poi quelli più vicini al completamento
  const traguardi = [...(dati?.traguardi ?? [])].sort(
    (a, b) => Number(b.ottenuto) - Number(a.ottenuto) || b.attuale / b.obiettivo - a.attuale / a.obiettivo,
  );
  const massimoArgomento = Math.max(10, ...(dati?.per_argomento.map((a) => a.esercizi) ?? [0]));

  return (
    <>
      <Intestazione
        etichetta="Tavola 06"
        titolo="Progressi"
        descrizione="I tuoi giorni di studio, gli esercizi per argomento e i traguardi raggiunti."
      />

      {errore && <p className="messaggio-errore">{errore}</p>}
      {!dati && !errore && <Caricamento testo="Conto i tuoi progressi…" />}

      {dati && (
        <div className="griglia-pannelli">
          {/* ----- numeri principali ----- */}
          <Pannello largo>
            <div className="cifre">
              <div className="cifra cifra-serie">
                <motion.strong key={dati.serie.attuale} initial={{ scale: 1.4, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}>
                  {dati.serie.attuale}
                </motion.strong>
                <span>{dati.serie.attuale === 1 ? "giorno di fila" : "giorni di fila"}</span>
                <small>
                  {dati.serie.studiato_oggi
                    ? "Oggi hai già studiato ✓"
                    : dati.serie.attuale > 0
                      ? "Studia oggi per non interrompere la serie"
                      : "Risolvi un esercizio per iniziare una serie"}
                </small>
              </div>
              <div className="cifra">
                <strong>{dati.serie.record}</strong>
                <span>record di giorni</span>
              </div>
              <div className="cifra">
                <strong>{dati.totali.esercizi}</strong>
                <span>esercizi risolti</span>
              </div>
              <div className="cifra">
                <strong>{dati.totali.risposte_giuste}</strong>
                <span>risposte giuste</span>
              </div>
              <div className="cifra">
                <strong>{dati.totali.fatti_da_te}</strong>
                <span>esercizi fatti da te</span>
              </div>
            </div>
          </Pannello>

          {/* ----- calendario ----- */}
          <Pannello titolo={`Giorni di studio · ultime 15 settimane (${dati.totali.giorni_di_studio} in tutto)`} largo>
            {/* Su schermi stretti il calendario scorre: partiamo da destra, cioè da oggi */}
            <div className="calendario-contenitore" ref={(div) => {
                if (div) div.scrollLeft = div.scrollWidth;
              }}
            >
              <Calendario giorni={dati.calendario} />
            </div>
            <p className="nota">Ogni quadretto è un giorno: più è pieno, più esercizi e risposte giuste hai fatto quel giorno.</p>
          </Pannello>

          {/* ----- esercizi per argomento ----- */}
          {["Analisi I", "Analisi II"].map((corso) => (
            <Pannello key={corso} titolo={`Esercizi risolti · ${corso}`}>
              <ul className="mappa-elenco">
                {dati.per_argomento
                  .filter((a) => a.corso === corso)
                  .map((a) => (
                    <li key={a.argomento} className="mappa-riga">
                      <div className="mappa-testa">
                        <span>{a.argomento}</span>
                        <span className="mappa-percentuale">{a.esercizi}</span>
                      </div>
                      <div className="barra-copertura" aria-hidden="true">
                        <motion.div
                          className="barra-copertura-piena"
                          initial={{ width: 0 }}
                          animate={{ width: `${(100 * a.esercizi) / massimoArgomento}%` }}
                          transition={{ duration: 0.8, ease: "easeOut" }}
                        />
                      </div>
                    </li>
                  ))}
              </ul>
            </Pannello>
          ))}

          {/* ----- traguardi ----- */}
          <Pannello titolo={`Traguardi · ${ottenuti} di ${dati.traguardi.length}`} largo>
            <ul className="traguardi">
              {traguardi.map((t, i) => (
                <motion.li
                  key={t.chiave}
                  className={"traguardo" + (t.ottenuto ? " ottenuto" : "")}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: Math.min(i, 12) * 0.04 }}
                >
                  <Timbro simbolo={t.simbolo} ottenuto={t.ottenuto} />
                  <div className="traguardo-testo">
                    <strong>{t.titolo}</strong>
                    <span>{t.descrizione}</span>
                    {t.ottenuto ? (
                      <small>Raggiunto il {new Date(t.ottenuto_il!).toLocaleDateString("it-IT")}</small>
                    ) : (
                      <>
                        <div className="barra-copertura" aria-label={`${t.attuale} di ${t.obiettivo}`}>
                          <div className="barra-copertura-piena" style={{ width: `${(100 * t.attuale) / t.obiettivo}%` }} />
                        </div>
                        <small>
                          {t.attuale} / {t.obiettivo}
                        </small>
                      </>
                    )}
                  </div>
                </motion.li>
              ))}
            </ul>
            {dati.totali.esercizi === 0 && (
              <p className="nota" style={{ marginTop: 14 }}>
                <Link to="/">Risolvi il primo esercizio</Link> per sbloccare il primo traguardo.
              </p>
            )}
          </Pannello>
        </div>
      )}
    </>
  );
}

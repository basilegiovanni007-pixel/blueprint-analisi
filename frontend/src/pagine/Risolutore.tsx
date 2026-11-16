// Pagina principale: lo studente scrive (o carica da file) un esercizio e riceve
// la soluzione passo passo, con le fonti prese dal suo Magazzino.
import { useState } from "react";

import { risolvi, type Soluzione } from "../api/client";
import Caricamento from "../componenti/Caricamento";
import EserciziDaFile from "../componenti/EserciziDaFile";
import Intestazione from "../componenti/Intestazione";
import Pannello from "../componenti/Pannello";
import VistaSoluzione from "../componenti/VistaSoluzione";

// Esempi pronti: un clic li copia nel riquadro e li risolve
const ESEMPI = [
  "limite per x che tende a 0 di sin(x)/x",
  "lim x->1 (x^2-1)/(x-1)",
  "derivata di x^2*sin(x)",
  "derivata di ln(cos(x))",
  "integrale di x*e^x dx",
  "integrale da 0 a pi di sin(x) dx",
  "serie di termine 1/n^2",
  "serie di termine (-1)^n/n",
  "y' + 2y = e^x",
  "y'' + 4y = 0, y(0) = 1, y'(0) = 2",
  // Analisi II
  "gradiente di x^2*y + y^3",
  "punti critici di x^3 + y^3 - 3*x*y",
  "massimi e minimi di x*y con vincolo x^2 + y^2 = 1",
  "integrale doppio di x*y con x da 0 a 1 e y da 0 a x",
];

const TIPI = [
  { valore: "auto", nome: "Riconosci da solo" },
  { valore: "limite", nome: "Limite" },
  { valore: "derivata", nome: "Derivata" },
  { valore: "integrale", nome: "Integrale" },
  { valore: "serie", nome: "Serie numerica" },
  { valore: "edo", nome: "Equazione differenziale" },
  { valore: "gradiente", nome: "Gradiente (più variabili)" },
  { valore: "critici", nome: "Punti critici (due variabili)" },
  { valore: "vincolati", nome: "Massimi e minimi vincolati" },
  { valore: "doppio", nome: "Integrale doppio" },
];

export default function Risolutore() {
  const [testo, setTesto] = useState("");
  const [tipo, setTipo] = useState("auto");
  const [soluzione, setSoluzione] = useState<Soluzione | null>(null);
  const [testoRisolto, setTestoRisolto] = useState("");
  const [daFoto, setDaFoto] = useState(false); // il testo nel riquadro viene da una foto?
  const [errore, setErrore] = useState("");
  const [inCorso, setInCorso] = useState(false);

  // Chiede la soluzione al backend. "esercizio" permette di risolvere subito un testo
  // appena scelto (da un esempio o da un file) senza aspettare che React aggiorni "testo".
  async function avvia(esercizio = testo, tipoScelto = tipo) {
    if (!esercizio.trim()) return;
    setInCorso(true);
    setErrore("");
    setSoluzione(null);
    try {
      setSoluzione(await risolvi(esercizio, tipoScelto));
      setTestoRisolto(esercizio); // il testo può cambiare dopo: teniamo quello davvero risolto
      setDaFoto(false); // risolto: l'avviso sul testo letto dalla foto non serve più
    } catch (e) {
      setErrore((e as Error).message);
    }
    setInCorso(false);
  }

  function usa(esercizio: string) {
    setTesto(esercizio);
    setTipo("auto");
    setDaFoto(false);
    avvia(esercizio, "auto");
  }

  // Esercizio letto da una foto: lo mettiamo nel riquadro, da controllare prima di risolvere
  function daControllare(esercizio: string) {
    setTesto(esercizio);
    setTipo("auto");
    setSoluzione(null);
    setErrore("");
    setDaFoto(true);
    window.scrollTo({ top: 0, behavior: "smooth" }); // il riquadro dell'esercizio è in alto
  }

  return (
    <>
      <Intestazione
        etichetta="Tavola 01"
        titolo="Risolutore"
        descrizione="Scrivi un esercizio di Analisi e ottieni la soluzione passo passo, con le fonti prese dal tuo Magazzino."
      />

      <div className="griglia-pannelli">
        <Pannello titolo="Esercizio" largo classe="non-stampare">
          <textarea
            className="campo-esercizio"
            value={testo}
            onChange={(e) => setTesto(e.target.value)}
            onKeyDown={(e) => {
              // Ctrl+Invio risolve senza dover usare il mouse
              if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) avvia();
            }}
            placeholder="Scrivi a parole o in LaTeX. Esempio: limite per x che tende a 0 di sin(x)/x"
            aria-label="Testo dell'esercizio"
          />
          {daFoto && (
            <p className="messaggio-avviso" style={{ margin: "12px 0 0" }}>
              Esercizio letto da una foto: controlla che formule e numeri siano giusti (per esempio x^2, sin(x),
              frazioni) e correggili qui sopra, poi premi Risolvi.
            </p>
          )}
          <div className="riga-azioni">
            <button className="bottone" onClick={() => avvia()} disabled={inCorso || !testo.trim()}>
              {inCorso ? "Risolvo…" : "Risolvi"}
            </button>
            <label className="campo campo-in-linea">
              <span>Tipo</span>
              <select value={tipo} onChange={(e) => setTipo(e.target.value)}>
                {TIPI.map((t) => (
                  <option key={t.valore} value={t.valore}>
                    {t.nome}
                  </option>
                ))}
              </select>
            </label>
            <span className="nota">Ctrl + Invio per risolvere</span>
          </div>

          <div className="esempi">
            <span className="nota">Prova con:</span>
            {ESEMPI.map((esempio) => (
              <button key={esempio} className="esempio" onClick={() => usa(esempio)} disabled={inCorso}>
                {esempio}
              </button>
            ))}
          </div>
        </Pannello>

        <Pannello titolo="Oppure risolvi da un file" largo classe="non-stampare">
          <EserciziDaFile onScelto={usa} onDaControllare={daControllare} />
        </Pannello>

        {errore && (
          <p className="messaggio-errore pannello-largo" role="alert">
            {errore}
          </p>
        )}

        {inCorso && (
          <div className="pannello-largo">
            <Caricamento testo="Sto risolvendo l'esercizio…" />
          </div>
        )}

        {soluzione && <VistaSoluzione soluzione={soluzione} testo={testoRisolto} />}
      </div>
    </>
  );
}

// Somme di Riemann: l'area sotto una curva approssimata con dei rettangoli.
// Aumentando il numero di rettangoli la somma si avvicina all'integrale.
import { useMemo, useState } from "react";

import { preparaFunzione } from "../api/client";
import Formula from "../componenti/Formula";
import Grafico, { type Elemento } from "../componenti/Grafico";
import Pannello from "../componenti/Pannello";
import CampoFunzione from "./CampoFunzione";
import Cursore from "./Cursore";
import { compila, formatta, integraleNumerico, leggiNumero } from "./calcolo";
import { useRichiesta } from "./useRichiesta";

const ESEMPI = ["x^2", "sin(x)", "e^(-x^2)", "1/x", "sqrt(x)"];

// Dove si misura l'altezza di ogni rettangolo: a sinistra, a destra o al centro della base
const METODI = [
  { valore: 0, nome: "Estremo sinistro" },
  { valore: 0.5, nome: "Punto medio" },
  { valore: 1, nome: "Estremo destro" },
];

export default function Riemann() {
  const [testo, setTesto] = useState("x^2");
  const [testoA, setTestoA] = useState("0");
  const [testoB, setTestoB] = useState("2");
  const [n, setN] = useState(6);
  const [posizione, setPosizione] = useState(0);

  const { dati, errore } = useRichiesta(() => preparaFunzione(testo), [testo], testo.trim() !== "");
  const conParametri = dati && dati.parametri.length > 0;
  const f = useMemo(() => (dati && !conParametri ? compila(dati.js, dati.variabile) : null), [dati, conParametri]);

  const a = leggiNumero(testoA);
  const b = leggiNumero(testoB);
  const estremiValidi = Number.isFinite(a) && Number.isFinite(b) && a < b;

  // Costruiamo i rettangoli e sommiamo le loro aree
  const { rettangoli, somma } = useMemo(() => {
    const rettangoli: Elemento[] = [];
    let somma = 0;
    if (f && estremiValidi) {
      const base = (b - a) / n;
      for (let i = 0; i < n; i++) {
        const sinistra = a + i * base;
        const altezza = f(sinistra + posizione * base);
        if (Number.isFinite(altezza)) {
          rettangoli.push({ tipo: "rettangolo", x1: sinistra, x2: sinistra + base, y: altezza });
          somma += altezza * base;
        }
      }
    }
    return { rettangoli, somma };
  }, [f, a, b, n, posizione, estremiValidi]);

  const esatto = f && estremiValidi ? integraleNumerico(f, a, b) : NaN;
  const margine = estremiValidi ? (b - a) * 0.25 : 1;
  const v = (numero: number) => formatta(numero, 6).replace(",", "{,}"); // numero pronto per KaTeX

  let messaggio = errore;
  if (conParametri) messaggio = "Qui serve una funzione della sola x, senza altre lettere.";
  else if (!estremiValidi) messaggio = "Gli estremi devono essere due numeri, con a minore di b (puoi scrivere anche pi o e).";

  return (
    <div className="griglia-pannelli">
      <Pannello titolo="Funzione e intervallo" largo>
        <CampoFunzione etichetta="f(x) =" valore={testo} onCambia={setTesto} esempi={ESEMPI} errore={messaggio}>
          <label className="campo campo-stretto">
            <span>da a =</span>
            <input value={testoA} onChange={(e) => setTestoA(e.target.value)} />
          </label>
          <label className="campo campo-stretto">
            <span>a b =</span>
            <input value={testoB} onChange={(e) => setTestoB(e.target.value)} />
          </label>
        </CampoFunzione>
      </Pannello>

      {dati && f && estremiValidi && (
        <Pannello titolo="Somma di Riemann" largo>
          <div className="cursori">
            <Cursore etichetta="numero di rettangoli n" valore={n} min={1} max={120} passo={1} onCambia={setN} />
            <label className="campo">
              <span>Altezza misurata in</span>
              <select value={posizione} onChange={(e) => setPosizione(Number(e.target.value))}>
                {METODI.map((m) => (
                  <option key={m.valore} value={m.valore}>
                    {m.nome}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <Grafico
            chiave={`${dati.js}|${a}|${b}`}
            finestra={{ xmin: a - margine, xmax: b + margine }}
            curve={[{ id: "f", f }]}
            elementi={rettangoli}
            descrizione={`Somma di Riemann di ${testo} con ${n} rettangoli`}
          />
          <div className="letture">
            <div className="lettura">
              <small>Somma delle aree dei {n} rettangoli</small>
              <Formula latex={`S_{${n}} = ${v(somma)}`} />
            </div>
            <div className="lettura">
              <small>Integrale (valore numerico di riferimento)</small>
              <Formula latex={`\\int_{${v(a)}}^{${v(b)}} ${dati.latex} \\, dx \\approx ${v(esatto)}`} />
            </div>
            <div className="lettura">
              <small>Differenza</small>
              <Formula latex={v(Math.abs(somma - esatto))} />
            </div>
          </div>
          <p className="nota">Aumenta n: i rettangoli diventano più stretti e la differenza si avvicina a zero.</p>
        </Pannello>
      )}
    </div>
  );
}

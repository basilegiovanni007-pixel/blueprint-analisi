// Mappa "vista dall'alto" di una funzione f(x, y): curve di livello, campo del gradiente,
// punti critici colorati per tipo, curva del vincolo e dominio di integrazione.
import { useMemo, useRef, useState } from "react";

import type { DatiSuperficie } from "../api/client";
import { compila2, formatta } from "../grafici/calcolo";
import { COLORI_PUNTI, curvaDiLivello, griglia, scegliLivelli, type Segmento, type Zona } from "../grafici/livelli";
import { tacche } from "./Grafico";

const LATO = 460; // il disegno è un quadrato: così cerchi e angoli retti non vengono deformati
const QUANTI_LIVELLI = 14;
const FRECCE_PER_LATO = 13;

type Props = {
  dati: DatiSuperficie;
  mostraGradiente: boolean;
};

/** Colore di una curva di livello: dal blu chiaro (valori bassi) al giallo (valori alti). */
function coloreLivello(posizione: number): string {
  const da = [95, 143, 214]; // blu chiaro
  const a = [255, 216, 102]; // giallo
  const c = da.map((v, i) => Math.round(v + (a[i] - v) * posizione));
  return `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
}

const comePercorso = (segmenti: Segmento[], px: (x: number) => number, py: (y: number) => number) =>
  segmenti.map(([x1, y1, x2, y2]) => `M${px(x1).toFixed(1)},${py(y1).toFixed(1)}L${px(x2).toFixed(1)},${py(y2).toFixed(1)}`).join("");

export default function MappaLivello({ dati, mostraGradiente }: Props) {
  const svg = useRef<SVGSVGElement>(null);
  const [mouse, setMouse] = useState<{ x: number; y: number } | null>(null);

  const f = useMemo(() => compila2(dati.funzione, dati.variabili), [dati]);

  // Zona quadrata: allarghiamo il lato più corto, così le due scale sono uguali
  const zona: Zona = useMemo(() => {
    const { xmin, xmax, ymin, ymax } = dati.finestra;
    const lato = Math.max(xmax - xmin, ymax - ymin);
    const cx = (xmin + xmax) / 2;
    const cy = (ymin + ymax) / 2;
    return { xmin: cx - lato / 2, xmax: cx + lato / 2, ymin: cy - lato / 2, ymax: cy + lato / 2 };
  }, [dati]);

  const px = (x: number) => ((x - zona.xmin) / (zona.xmax - zona.xmin)) * LATO;
  const py = (y: number) => LATO - ((y - zona.ymin) / (zona.ymax - zona.ymin)) * LATO;

  // Tutto ciò che è costoso da calcolare viene rifatto solo quando cambiano i dati
  const disegno = useMemo(() => {
    const valori = griglia(f, zona, 90);
    const livelli = scegliLivelli(valori, QUANTI_LIVELLI).map((livello, k) => ({
      d: comePercorso(curvaDiLivello(valori, zona, livello), px, py),
      colore: coloreLivello(k / (QUANTI_LIVELLI - 1)),
    }));

    // Curva del vincolo g(x, y) = 0
    let vincolo = "";
    if (dati.vincolo) {
      const g = compila2(dati.vincolo, dati.variabili);
      vincolo = comePercorso(curvaDiLivello(griglia(g, zona, 160), zona, 0), px, py);
    }

    // Dominio di integrazione: il bordo inferiore percorso in avanti, quello superiore all'indietro
    let dominio = "";
    if (dati.dominio) {
      const d = dati.dominio;
      const inferiore = compila2(d.inferiore, dati.variabili);
      const superiore = compila2(d.superiore, dati.variabili);
      const orizzontale = d.esterna === dati.variabili[0]; // la variabile esterna è quella sull'asse x?
      const punto = (t: number, bordo: typeof inferiore) => {
        const valore = orizzontale ? bordo(t, 0) : bordo(0, t);
        return orizzontale ? `${px(t).toFixed(1)},${py(valore).toFixed(1)}` : `${px(valore).toFixed(1)},${py(t).toFixed(1)}`;
      };
      const passi = 60;
      const vertici: string[] = [];
      for (let i = 0; i <= passi; i++) vertici.push(punto(d.a + ((d.b - d.a) * i) / passi, inferiore));
      for (let i = passi; i >= 0; i--) vertici.push(punto(d.a + ((d.b - d.a) * i) / passi, superiore));
      dominio = vertici.join(" ");
    }

    // Campo del gradiente: una freccia per ogni nodo di una griglia rada
    const frecce: { x1: number; y1: number; x2: number; y2: number }[] = [];
    const passo = (zona.xmax - zona.xmin) / FRECCE_PER_LATO;
    const h = passo * 1e-3;
    const grezze: { x: number; y: number; gx: number; gy: number; modulo: number }[] = [];
    for (let j = 0; j < FRECCE_PER_LATO; j++) {
      for (let i = 0; i < FRECCE_PER_LATO; i++) {
        const x = zona.xmin + (i + 0.5) * passo;
        const y = zona.ymin + (j + 0.5) * passo;
        const gx = (f(x + h, y) - f(x - h, y)) / (2 * h);
        const gy = (f(x, y + h) - f(x, y - h)) / (2 * h);
        const modulo = Math.hypot(gx, gy);
        if (Number.isFinite(modulo) && modulo > 0) grezze.push({ x, y, gx, gy, modulo });
      }
    }
    // Lunghezza: proporzionale al modulo del gradiente, ma mai più lunga di una casella
    const moduli = grezze.map((g) => g.modulo).sort((p, q) => p - q);
    const riferimento = moduli[Math.floor(moduli.length * 0.9)] || 1;
    for (const g of grezze) {
      const lunghezza = passo * 0.85 * Math.min(1, Math.max(0.18, g.modulo / riferimento));
      frecce.push({
        x1: px(g.x),
        y1: py(g.y),
        x2: px(g.x + (g.gx / g.modulo) * lunghezza),
        y2: py(g.y + (g.gy / g.modulo) * lunghezza),
      });
    }
    return { livelli, vincolo, dominio, frecce };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [f, zona, dati]);

  const valoreMouse = mouse ? f(mouse.x, mouse.y) : NaN;

  return (
    <div className="grafico mappa">
      <svg
        ref={svg}
        viewBox={`0 0 ${LATO} ${LATO}`}
        role="img"
        aria-label="Mappa delle curve di livello"
        onPointerMove={(e) => {
          const r = svg.current!.getBoundingClientRect();
          setMouse({
            x: zona.xmin + ((e.clientX - r.left) / r.width) * (zona.xmax - zona.xmin),
            y: zona.ymax - ((e.clientY - r.top) / r.height) * (zona.ymax - zona.ymin),
          });
        }}
        onPointerLeave={() => setMouse(null)}
      >
        <defs>
          {/* La punta delle frecce del gradiente */}
          <marker id="punta" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto">
            <path d="M0,0 L10,5 L0,10 z" fill="var(--bianco)" />
          </marker>
        </defs>

        {/* Dominio di integrazione */}
        {disegno.dominio && <polygon points={disegno.dominio} className="mappa-dominio" />}

        {/* Assi e numeri */}
        <line x1={0} x2={LATO} y1={py(0)} y2={py(0)} className="grafico-asse" />
        <line x1={px(0)} x2={px(0)} y1={0} y2={LATO} className="grafico-asse" />
        {tacche(zona.xmin, zona.xmax).map((x) =>
          x !== 0 ? (
            <text key={"x" + x} x={px(x)} y={Math.max(12, Math.min(LATO - 5, py(0) + 13))} textAnchor="middle" className="grafico-numero">
              {formatta(x)}
            </text>
          ) : null,
        )}
        {tacche(zona.ymin, zona.ymax).map((y) =>
          y !== 0 ? (
            <text key={"y" + y} x={Math.max(4, Math.min(LATO - 28, px(0) + 5))} y={py(y) + 4} className="grafico-numero">
              {formatta(y)}
            </text>
          ) : null,
        )}
        <text x={LATO - 10} y={py(0) - 7} textAnchor="end" className="grafico-etichetta">
          {dati.variabili[0]}
        </text>
        <text x={px(0) + 8} y={14} className="grafico-etichetta">
          {dati.variabili[1]}
        </text>

        {/* Curve di livello */}
        {disegno.livelli.map((livello, k) => (
          <path key={k} d={livello.d} stroke={livello.colore} className="mappa-livello" />
        ))}

        {/* Campo del gradiente */}
        {mostraGradiente &&
          disegno.frecce.map((freccia, k) => <line key={k} {...freccia} className="mappa-freccia" markerEnd="url(#punta)" />)}

        {/* Curva del vincolo */}
        {disegno.vincolo && <path d={disegno.vincolo} className="mappa-vincolo" />}

        {/* Punti notevoli, colorati per tipo */}
        {dati.punti.map((p, k) => (
          <circle key={k} cx={px(p.x)} cy={py(p.y)} r={6} fill={COLORI_PUNTI[p.tipo] ?? "#f4f8ff"} className="mappa-punto" />
        ))}

        {/* Valore della funzione sotto il mouse */}
        {mouse && Number.isFinite(valoreMouse) && (
          <text
            x={px(mouse.x) + (px(mouse.x) > LATO - 190 ? -10 : 10)}
            y={Math.max(16, py(mouse.y) - 10)}
            textAnchor={px(mouse.x) > LATO - 190 ? "end" : "start"}
            className="grafico-coordinate"
            pointerEvents="none"
          >
            f({formatta(mouse.x, 3)} ; {formatta(mouse.y, 3)}) = {formatta(valoreMouse)}
          </text>
        )}
      </svg>
    </div>
  );
}

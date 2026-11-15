// Grafico interattivo in stile blueprint, disegnato in SVG.
// - trascina per spostarti, Ctrl + rotella (o pulsanti) per lo zoom, doppio clic per tornare all'inizio;
// - passando il mouse compare un cursore con le coordinate del punto sulla curva;
// - le curve possono "disegnarsi" con un'animazione a tratto, come una matita.
import { useEffect, useMemo, useRef, useState, type PointerEvent as EventoPuntatore } from "react";

import { formatta, type Funzione } from "../grafici/calcolo";

// ---------- cosa si può disegnare ----------

export type Curva = {
  id: string;
  f: Funzione;
  stile?: "principale" | "seconda" | "tenue";
  disegna?: boolean; // true = compare con l'animazione "a matita"
  visibile?: boolean; // false = non disegnata, ma usata per scegliere la scala verticale
};

export type Elemento =
  | { tipo: "punto"; x: number; y: number; etichetta?: string; stile?: string }
  | { tipo: "verticale"; x: number; etichetta?: string }
  | { tipo: "orizzontale"; y: number; etichetta?: string }
  | { tipo: "retta"; m: number; q: number; etichetta?: string; stile?: string }
  | { tipo: "fascia"; da: number | null; a: number | null; stile?: string }
  | { tipo: "rettangolo"; x1: number; x2: number; y: number }
  | { tipo: "area"; da: number; a: number }
  | { tipo: "segmento"; x1: number; y1: number; x2: number; y2: number }
  | { tipo: "curva" }; // segnaposto usato dallo studio di funzione (qui non disegna nulla)

export type Finestra = { xmin: number; xmax: number; ymin?: number; ymax?: number };
type Vista = { xmin: number; xmax: number; ymin: number; ymax: number };

type Props = {
  curve: Curva[];
  elementi?: Elemento[];
  finestra: Finestra; // la zona mostrata all'inizio (se manca la y viene scelta da sola)
  chiave?: string | number; // quando cambia, il grafico torna alla finestra iniziale
  descrizione?: string; // testo per chi usa un lettore di schermo
};

// Dimensioni "logiche" del disegno: l'SVG poi si adatta alla larghezza disponibile
const LARGHEZZA = 720;
const ALTEZZA = 430;
const CAMPIONI = 480; // in quanti punti calcoliamo la funzione per disegnarla

// ---------- funzioni di supporto ----------

/** Sceglie la scala verticale guardando i valori della funzione nella zona mostrata. */
function scalaAutomatica(curve: Curva[], elementi: Elemento[], xmin: number, xmax: number): [number, number] {
  const valori: number[] = [];
  // La scala si decide sulla curva principale: le altre (derivata, polinomi...) si adattano
  const principali = curve.filter((c) => (c.stile ?? "principale") === "principale");
  for (const curva of principali.length > 0 ? principali : curve) {
    for (let i = 0; i <= 300; i++) {
      const y = curva.f(xmin + ((xmax - xmin) * i) / 300);
      if (Number.isFinite(y)) valori.push(y);
    }
  }
  if (valori.length === 0) return [-5, 5];
  valori.sort((a, b) => a - b);
  // Scartiamo il 4% dei valori più estremi: così un asintoto non schiaccia tutto il resto
  let basso = valori[Math.floor(valori.length * 0.04)];
  let alto = valori[Math.ceil(valori.length * 0.96) - 1];
  // I punti importanti (massimi, minimi, zeri...) devono essere visibili
  for (const e of elementi) {
    if (e.tipo === "punto" || e.tipo === "orizzontale") {
      basso = Math.min(basso, e.y);
      alto = Math.max(alto, e.y);
    }
  }
  if (alto - basso < 1e-9) {
    basso -= 1;
    alto += 1;
  }
  // Mostriamo anche l'asse x, se non è troppo lontano
  const ampiezza = alto - basso;
  if (basso > 0 && basso < ampiezza) basso = 0;
  if (alto < 0 && -alto < ampiezza) alto = 0;
  const margine = (alto - basso) * 0.15;
  return [basso - margine, alto + margine];
}

/** Passo "tondo" per la griglia (1, 2, 5, 10, 20, 50...) in base a quanto è larga la zona mostrata. */
function passoGriglia(ampiezza: number): number {
  const grezzo = ampiezza / 8;
  const potenza = Math.pow(10, Math.floor(Math.log10(grezzo)));
  const rapporto = grezzo / potenza;
  return potenza * (rapporto < 1.5 ? 1 : rapporto < 3.5 ? 2 : rapporto < 7.5 ? 5 : 10);
}

export function tacche(min: number, max: number): number[] {
  const passo = passoGriglia(max - min);
  const elenco: number[] = [];
  for (let v = Math.ceil(min / passo) * passo; v <= max; v += passo) {
    elenco.push(Math.abs(v) < passo / 1000 ? 0 : v);
  }
  return elenco;
}

// ---------- il componente ----------

export default function Grafico({ curve, elementi = [], finestra, chiave, descrizione }: Props) {
  const iniziale = (): Vista => {
    const [ymin, ymax] =
      finestra.ymin !== undefined && finestra.ymax !== undefined
        ? [finestra.ymin, finestra.ymax]
        : scalaAutomatica(curve, elementi, finestra.xmin, finestra.xmax);
    return { xmin: finestra.xmin, xmax: finestra.xmax, ymin, ymax };
  };

  const [vista, setVista] = useState<Vista>(iniziale);
  const [cursore, setCursore] = useState<number | null>(null); // ascissa sotto il mouse
  const svg = useRef<SVGSVGElement>(null);
  const trascinamento = useRef<{ x: number; y: number; vista: Vista } | null>(null);

  // Quando cambia la funzione (chiave diversa) torniamo alla finestra iniziale
  useEffect(() => {
    setVista(iniziale());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chiave]);

  // Conversioni tra coordinate matematiche e pixel del disegno
  const px = (x: number) => ((x - vista.xmin) / (vista.xmax - vista.xmin)) * LARGHEZZA;
  const py = (y: number) => ALTEZZA - ((y - vista.ymin) / (vista.ymax - vista.ymin)) * ALTEZZA;
  const altezzaVista = vista.ymax - vista.ymin;
  // Evita coordinate enormi (vicino agli asintoti) che metterebbero in difficoltà il browser
  const limita = (y: number) => Math.max(vista.ymin - 3 * altezzaVista, Math.min(vista.ymax + 3 * altezzaVista, y));

  /** Posizione del mouse in coordinate matematiche. */
  function posizione(evento: { clientX: number; clientY: number }) {
    const riquadro = svg.current!.getBoundingClientRect();
    return {
      x: vista.xmin + ((evento.clientX - riquadro.left) / riquadro.width) * (vista.xmax - vista.xmin),
      y: vista.ymax - ((evento.clientY - riquadro.top) / riquadro.height) * altezzaVista,
    };
  }

  /** Zoom attorno a un punto: fattore < 1 ingrandisce, > 1 rimpicciolisce. */
  function zoom(fattore: number, centro?: { x: number; y: number }) {
    setVista((v) => {
      const c = centro ?? { x: (v.xmin + v.xmax) / 2, y: (v.ymin + v.ymax) / 2 };
      const nuova = {
        xmin: c.x - (c.x - v.xmin) * fattore,
        xmax: c.x + (v.xmax - c.x) * fattore,
        ymin: c.y - (c.y - v.ymin) * fattore,
        ymax: c.y + (v.ymax - c.y) * fattore,
      };
      // Limiti di buon senso: né troppo vicino né troppo lontano
      const ampiezza = nuova.xmax - nuova.xmin;
      return ampiezza < 1e-6 || ampiezza > 1e6 ? v : nuova;
    });
  }

  // La rotella va collegata "a mano": solo così possiamo impedire che scorra anche la pagina
  useEffect(() => {
    const elemento = svg.current;
    if (!elemento) return;
    const suRotella = (evento: WheelEvent) => {
      // Lo zoom richiede Ctrl (o il "pizzico" sul touchpad): senza, la rotella scorre la pagina
      // come al solito, così non si resta "incastrati" sul grafico mentre si legge.
      if (!evento.ctrlKey && !evento.metaKey) return;
      evento.preventDefault();
      zoom(evento.deltaY > 0 ? 1.15 : 1 / 1.15, posizione(evento));
    };
    elemento.addEventListener("wheel", suRotella, { passive: false });
    return () => elemento.removeEventListener("wheel", suRotella);
  });

  function inizioTrascinamento(evento: EventoPuntatore<SVGSVGElement>) {
    evento.currentTarget.setPointerCapture(evento.pointerId);
    trascinamento.current = { x: evento.clientX, y: evento.clientY, vista };
  }

  function movimento(evento: EventoPuntatore<SVGSVGElement>) {
    const inizio = trascinamento.current;
    if (!inizio) {
      setCursore(posizione(evento).x);
      return;
    }
    // Spostiamo la vista di quanto si è mosso il puntatore
    const riquadro = svg.current!.getBoundingClientRect();
    const dx = ((evento.clientX - inizio.x) / riquadro.width) * (inizio.vista.xmax - inizio.vista.xmin);
    const dy = ((evento.clientY - inizio.y) / riquadro.height) * (inizio.vista.ymax - inizio.vista.ymin);
    setVista({
      xmin: inizio.vista.xmin - dx,
      xmax: inizio.vista.xmax - dx,
      ymin: inizio.vista.ymin + dy,
      ymax: inizio.vista.ymax + dy,
    });
  }

  /** Costruisce il tracciato SVG di una funzione, interrompendolo dove non esiste o "salta". */
  function tracciato(f: Funzione, da = vista.xmin, a = vista.xmax): string {
    let percorso = "";
    let precedente: number | null = null;
    for (let i = 0; i <= CAMPIONI; i++) {
      const x = da + ((a - da) * i) / CAMPIONI;
      const y = f(x);
      // Un salto enorme tra due punti vicini è un asintoto: lì la linea va interrotta
      const salto = precedente !== null && Math.abs(y - precedente) > 2.5 * altezzaVista;
      if (!Number.isFinite(y)) {
        precedente = null;
        continue;
      }
      percorso += `${precedente === null || salto ? "M" : "L"}${px(x).toFixed(1)},${py(limita(y)).toFixed(1)} `;
      precedente = y;
    }
    return percorso;
  }

  // I tracciati vengono ricalcolati solo quando cambiano le curve o la vista
  const tracciati = useMemo(
    () => curve.filter((c) => c.visibile !== false).map((c) => ({ curva: c, d: tracciato(c.f) })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [curve, vista],
  );

  const principale = curve.find((c) => c.visibile !== false && (c.stile ?? "principale") === "principale");
  const tacheX = tacche(vista.xmin, vista.xmax);
  const tacheY = tacche(vista.ymin, vista.ymax);
  // Se un asse esce dalla vista, i numeri restano attaccati al bordo
  const yAsse = Math.max(14, Math.min(ALTEZZA - 6, py(0) + 14));
  const xAsse = Math.max(4, Math.min(LARGHEZZA - 30, px(0) + 5));

  const yCursore = cursore !== null && principale ? principale.f(cursore) : NaN;

  return (
    <div className="grafico">
      <svg
        ref={svg}
        viewBox={`0 0 ${LARGHEZZA} ${ALTEZZA}`}
        role="img"
        aria-label={descrizione ?? "Grafico interattivo"}
        onPointerDown={inizioTrascinamento}
        onPointerMove={movimento}
        onPointerUp={() => (trascinamento.current = null)}
        onPointerLeave={() => {
          trascinamento.current = null;
          setCursore(null);
        }}
        onDoubleClick={() => setVista(iniziale())}
      >
        <defs>
          {/* Tratteggio obliquo per le zone escluse dal dominio */}
          <pattern id="tratteggio" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <line x1="0" y1="0" x2="0" y2="8" stroke="var(--azzurrino)" strokeWidth="1" opacity="0.45" />
          </pattern>
        </defs>

        {/* Griglia tratteggiata */}
        {tacheX.map((x) => (
          <line key={"gx" + x} x1={px(x)} x2={px(x)} y1={0} y2={ALTEZZA} className="grafico-griglia" />
        ))}
        {tacheY.map((y) => (
          <line key={"gy" + y} x1={0} x2={LARGHEZZA} y1={py(y)} y2={py(y)} className="grafico-griglia" />
        ))}

        {/* Fasce (zone escluse dal dominio) */}
        {elementi.map((e, i) =>
          e.tipo === "fascia" ? (
            <rect
              key={"f" + i}
              x={Math.max(0, e.da === null ? 0 : px(e.da))}
              width={Math.max(0, Math.min(LARGHEZZA, e.a === null ? LARGHEZZA : px(e.a)) - Math.max(0, e.da === null ? 0 : px(e.da)))}
              y={0}
              height={ALTEZZA}
              fill="url(#tratteggio)"
            />
          ) : null,
        )}

        {/* Assi */}
        <line x1={0} x2={LARGHEZZA} y1={py(0)} y2={py(0)} className="grafico-asse" />
        <line x1={px(0)} x2={px(0)} y1={0} y2={ALTEZZA} className="grafico-asse" />
        {tacheX.map((x) =>
          x !== 0 ? (
            <text key={"tx" + x} x={px(x)} y={yAsse} className="grafico-numero" textAnchor="middle">
              {formatta(x)}
            </text>
          ) : null,
        )}
        {tacheY.map((y) =>
          y !== 0 ? (
            <text key={"ty" + y} x={xAsse} y={py(y) + 4} className="grafico-numero">
              {formatta(y)}
            </text>
          ) : null,
        )}

        {/* Area sotto la curva e rettangoli (integrali, somme di Riemann) */}
        {elementi.map((e, i) => {
          if (e.tipo === "area" && principale) {
            const da = Math.max(e.da, vista.xmin);
            const a = Math.min(e.a, vista.xmax);
            if (a <= da) return null;
            const bordo = tracciato(principale.f, da, a).replace(/M/g, "L").replace(/^L/, "");
            return <path key={"a" + i} d={`M${px(da)},${py(0)} L${bordo} L${px(a)},${py(0)} Z`} className="grafico-area" />;
          }
          if (e.tipo === "rettangolo") {
            const alto = py(Math.max(0, limita(e.y)));
            const basso = py(Math.min(0, limita(e.y)));
            return (
              <rect key={"r" + i} x={px(e.x1)} width={Math.max(0, px(e.x2) - px(e.x1))} y={alto} height={basso - alto} className="grafico-rettangolo" />
            );
          }
          return null;
        })}

        {/* Rette: asintoti, tangenti, secanti */}
        {elementi.map((e, i) => {
          if (e.tipo === "verticale") {
            return (
              <g key={"v" + i} className="grafico-comparsa">
                <line x1={px(e.x)} x2={px(e.x)} y1={0} y2={ALTEZZA} className="grafico-asintoto" />
                {e.etichetta && (
                  <text x={px(e.x) + 6} y={16} className="grafico-etichetta">
                    {e.etichetta}
                  </text>
                )}
              </g>
            );
          }
          if (e.tipo === "orizzontale") {
            return (
              <g key={"o" + i} className="grafico-comparsa">
                <line x1={0} x2={LARGHEZZA} y1={py(e.y)} y2={py(e.y)} className="grafico-asintoto" />
                {e.etichetta && (
                  <text x={LARGHEZZA - 8} y={py(e.y) - 6} className="grafico-etichetta" textAnchor="end">
                    {e.etichetta}
                  </text>
                )}
              </g>
            );
          }
          if (e.tipo === "retta") {
            const y1 = e.m * vista.xmin + e.q;
            const y2 = e.m * vista.xmax + e.q;
            return (
              <g key={"l" + i} className="grafico-comparsa">
                <line x1={0} x2={LARGHEZZA} y1={py(limita(y1))} y2={py(limita(y2))} className={"grafico-" + (e.stile ?? "asintoto")} />
                {e.etichetta && (
                  <text x={LARGHEZZA - 8} y={Math.max(14, Math.min(ALTEZZA - 6, py(y2) + (e.m > 0 ? 18 : -8)))} className="grafico-etichetta" textAnchor="end">
                    {e.etichetta}
                  </text>
                )}
              </g>
            );
          }
          if (e.tipo === "segmento") {
            return <line key={"s" + i} x1={px(e.x1)} y1={py(e.y1)} x2={px(e.x2)} y2={py(e.y2)} className="grafico-segmento" />;
          }
          return null;
        })}

        {/* Curve */}
        {tracciati.map(({ curva, d }) => (
          <path
            key={curva.id}
            d={d}
            pathLength={curva.disegna ? 1 : undefined}
            className={"grafico-curva grafico-curva-" + (curva.stile ?? "principale") + (curva.disegna ? " tratto-matita" : "")}
          />
        ))}

        {/* Punti notevoli */}
        {elementi.map((e, i) =>
          e.tipo === "punto" ? (
            <g key={"p" + i} className="grafico-comparsa">
              <circle cx={px(e.x)} cy={py(e.y)} r={e.stile === "piccolo" ? 2.5 : 5} className={"grafico-punto grafico-punto-" + (e.stile ?? "zero")} />
              {e.etichetta && (
                <text x={px(e.x) + 9} y={py(e.y) + (e.stile === "minimo" ? 18 : -9)} className="grafico-etichetta">
                  {e.etichetta}
                </text>
              )}
            </g>
          ) : null,
        )}

        {/* Cursore con le coordinate */}
        {cursore !== null && Number.isFinite(yCursore) && (
          <g pointerEvents="none">
            <line x1={px(cursore)} x2={px(cursore)} y1={0} y2={ALTEZZA} className="grafico-mirino" />
            <circle cx={px(cursore)} cy={py(yCursore)} r={4} className="grafico-mirino-punto" />
            <text
              x={px(cursore) + (px(cursore) > LARGHEZZA - 150 ? -10 : 10)}
              y={Math.max(16, py(yCursore) - 10)}
              textAnchor={px(cursore) > LARGHEZZA - 150 ? "end" : "start"}
              className="grafico-coordinate"
            >
              ({formatta(cursore)} ; {formatta(yCursore)})
            </text>
          </g>
        )}
      </svg>

      <div className="grafico-comandi">
        <button onClick={() => zoom(1 / 1.4)} aria-label="Ingrandisci" title="Ingrandisci">
          +
        </button>
        <button onClick={() => zoom(1.4)} aria-label="Rimpicciolisci" title="Rimpicciolisci">
          −
        </button>
        <button onClick={() => setVista(iniziale())} aria-label="Torna alla vista iniziale" title="Vista iniziale">
          ⟲
        </button>
      </div>
    </div>
  );
}

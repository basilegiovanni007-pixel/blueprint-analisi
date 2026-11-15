// Superficie 3D ruotabile di una funzione z = f(x, y), disegnata con la libreria Plotly.
// Si ruota trascinando; i pulsanti in alto a destra servono per zoom e vista iniziale.
import { useEffect, useRef, useState } from "react";

import type { DatiSuperficie } from "../api/client";
import { compila2 } from "../grafici/calcolo";
import { COLORI_PUNTI, NOMI_PUNTI, curvaDiLivello, griglia } from "../grafici/livelli";

const PUNTI_PER_LATO = 70; // quanto è fitta la griglia su cui si calcola la funzione

export default function Superficie3D({ dati }: { dati: DatiSuperficie }) {
  const contenitore = useRef<HTMLDivElement>(null);
  const [errore, setErrore] = useState("");
  // La libreria Plotly, una volta caricata (serve per poter cancellare il grafico al momento giusto)
  const plotly = useRef<{ purge: (elemento: HTMLElement) => void } | null>(null);

  useEffect(() => {
    let annullato = false;
    const elemento = contenitore.current;
    if (!elemento) return;

    // Plotly è una libreria pesante: la carichiamo solo quando serve davvero un grafico 3D
    import("plotly.js-gl3d-dist-min")
      .then((modulo) => {
        if (annullato) return;
        const Plotly = modulo.default ?? modulo;
        plotly.current = Plotly;
        const f = compila2(dati.funzione, dati.variabili);
        const zona = dati.finestra;
        // Con un dominio di integrazione usiamo una griglia più fitta, per un bordo meno "a scalini"
        const n = dati.dominio ? PUNTI_PER_LATO * 2 : PUNTI_PER_LATO;
        const xs = Array.from({ length: n + 1 }, (_, i) => zona.xmin + ((zona.xmax - zona.xmin) * i) / n);
        const ys = Array.from({ length: n + 1 }, (_, j) => zona.ymin + ((zona.ymax - zona.ymin) * j) / n);

        // Per gli integrali doppi mostriamo solo la parte di superficie sopra il dominio
        let nelDominio: (x: number, y: number) => boolean = () => true;
        if (dati.dominio) {
          const d = dati.dominio;
          const inferiore = compila2(d.inferiore, dati.variabili);
          const superiore = compila2(d.superiore, dati.variabili);
          nelDominio = (x, y) => {
            const [esterna, interna] = d.esterna === dati.variabili[0] ? [x, y] : [y, x];
            return esterna >= d.a && esterna <= d.b && interna >= inferiore(x, y) && interna <= superiore(x, y);
          };
        }

        const z: (number | null)[][] = ys.map((y) =>
          xs.map((x) => {
            const valore = f(x, y);
            return Number.isFinite(valore) && nelDominio(x, y) ? valore : null;
          }),
        );

        // Altezza mostrata: scartiamo i valori estremi, così un "picco" non appiattisce il resto
        const finiti = (z.flat().filter((v) => v !== null) as number[]).sort((p, q) => p - q);
        const basso = finiti[Math.floor(finiti.length * 0.005)] ?? -1;
        const alto = finiti[Math.ceil(finiti.length * 0.995) - 1] ?? 1;
        const margine = (alto - basso || 1) * 0.1;

        const tracce: unknown[] = [
          {
            type: "surface",
            x: xs,
            y: ys,
            z,
            cmin: basso,
            cmax: alto,
            colorscale: [
              [0, "#123a73"],
              [0.5, "#7fa9e6"],
              [1, "#ffd866"],
            ],
            showscale: false,
            opacity: 0.93,
            // Curve di livello: disegnate sulla superficie e proiettate sul "pavimento"
            contours: {
              z: { show: true, usecolormap: false, color: "rgba(244,248,255,0.55)", width: 1, project: { z: true } },
            },
            hovertemplate: `${dati.variabili[0]} = %{x:.2f}<br>${dati.variabili[1]} = %{y:.2f}<br>f = %{z:.3f}<extra></extra>`,
          },
        ];

        // La curva del vincolo, "appoggiata" sulla superficie
        if (dati.vincolo) {
          const g = compila2(dati.vincolo, dati.variabili);
          const zonaPiena = { xmin: zona.xmin, xmax: zona.xmax, ymin: zona.ymin, ymax: zona.ymax };
          const cx: (number | null)[] = [];
          const cy: (number | null)[] = [];
          const cz: (number | null)[] = [];
          for (const [x1, y1, x2, y2] of curvaDiLivello(griglia(g, zonaPiena, 140), zonaPiena, 0)) {
            cx.push(x1, x2, null); // "null" stacca un trattino dal successivo
            cy.push(y1, y2, null);
            cz.push(f(x1, y1), f(x2, y2), null);
          }
          tracce.push({ type: "scatter3d", mode: "lines", x: cx, y: cy, z: cz, line: { color: "#f4f8ff", width: 6 }, hoverinfo: "skip" });
        }

        // Punti notevoli, colorati per tipo
        if (dati.punti.length > 0) {
          tracce.push({
            type: "scatter3d",
            mode: "markers",
            x: dati.punti.map((p) => p.x),
            y: dati.punti.map((p) => p.y),
            z: dati.punti.map((p) => p.z),
            marker: {
              size: 6,
              color: dati.punti.map((p) => COLORI_PUNTI[p.tipo] ?? "#f4f8ff"),
              line: { color: "#061b40", width: 2 },
            },
            text: dati.punti.map((p) => NOMI_PUNTI[p.tipo] ?? p.tipo),
            hovertemplate: "%{text}<br>(%{x:.3f} ; %{y:.3f})<br>f = %{z:.3f}<extra></extra>",
          });
        }

        const asse = (titolo: string) => ({
          title: { text: titolo },
          color: "#f4f8ff",
          gridcolor: "rgba(200,222,255,0.22)",
          zerolinecolor: "rgba(244,248,255,0.8)",
          showbackground: false,
        });

        Plotly.react(
          elemento,
          tracce,
          {
            height: 430,
            margin: { l: 0, r: 0, t: 0, b: 0 },
            paper_bgcolor: "rgba(0,0,0,0)",
            showlegend: false,
            font: { family: "IBM Plex Mono, monospace", size: 11, color: "#f4f8ff" },
            scene: {
              bgcolor: "#061b40",
              xaxis: asse(dati.variabili[0]),
              yaxis: asse(dati.variabili[1]),
              zaxis: { ...asse("f"), range: [basso - margine, alto + margine] },
              camera: { eye: { x: 1.5, y: -1.6, z: 1.0 } },
              aspectmode: "cube",
            },
          },
          {
            responsive: true,
            scrollZoom: false, // la rotella deve scorrere la pagina, non ingrandire il grafico
            displaylogo: false,
            // Teniamo solo i pulsanti utili: zoom, rotazione e ritorno alla vista iniziale
            modeBarButtonsToRemove: ["toImage", "pan3d", "tableRotation", "resetCameraLastSave3d", "hoverClosest3d"],
          },
        );
      })
      .catch(() => setErrore("Non sono riuscito a disegnare il grafico 3D."));

    return () => {
      annullato = true;
      // Liberiamo subito la memoria usata dal grafico quando il componente sparisce o i dati cambiano.
      // (Va fatto all'istante e non "più tardi": altrimenti si rischia di cancellare il grafico nuovo.)
      plotly.current?.purge(elemento);
    };
  }, [dati]);

  if (errore) return <p className="messaggio-errore">{errore}</p>;
  return <div ref={contenitore} className="superficie" role="img" aria-label="Grafico 3D della superficie" />;
}

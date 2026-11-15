// Curve di livello: i punti in cui una funzione f(x, y) vale un certo numero.
// Per trovarle usiamo l'algoritmo "marching squares": si calcola f su una griglia e, in ogni
// quadratino, si guarda in quali lati la funzione attraversa il livello cercato.
import type { Funzione2 } from "./calcolo";

export type Zona = { xmin: number; xmax: number; ymin: number; ymax: number };
export type Segmento = [number, number, number, number]; // x1, y1, x2, y2

/** Calcola f su una griglia di (n+1) x (n+1) punti. valori[j][i] corrisponde a (x_i, y_j). */
export function griglia(f: Funzione2, zona: Zona, n: number): number[][] {
  const valori: number[][] = [];
  for (let j = 0; j <= n; j++) {
    const riga: number[] = [];
    const y = zona.ymin + ((zona.ymax - zona.ymin) * j) / n;
    for (let i = 0; i <= n; i++) {
      riga.push(f(zona.xmin + ((zona.xmax - zona.xmin) * i) / n, y));
    }
    valori.push(riga);
  }
  return valori;
}

/** Trova i trattini che compongono la curva di livello "livello" sulla griglia data. */
export function curvaDiLivello(valori: number[][], zona: Zona, livello: number): Segmento[] {
  const n = valori.length - 1;
  const dx = (zona.xmax - zona.xmin) / n;
  const dy = (zona.ymax - zona.ymin) / n;
  const segmenti: Segmento[] = [];

  for (let j = 0; j < n; j++) {
    for (let i = 0; i < n; i++) {
      // I quattro angoli del quadratino: basso-sinistra, basso-destra, alto-destra, alto-sinistra
      const a = valori[j][i] - livello;
      const b = valori[j][i + 1] - livello;
      const c = valori[j + 1][i + 1] - livello;
      const d = valori[j + 1][i] - livello;
      if (![a, b, c, d].every(Number.isFinite)) continue;

      const x0 = zona.xmin + i * dx;
      const y0 = zona.ymin + j * dy;
      // Punti in cui la curva attraversa i lati (trovati per proporzione tra i due angoli)
      const attraversamenti: [number, number][] = [];
      if (a * b < 0) attraversamenti.push([x0 + (a / (a - b)) * dx, y0]); // lato in basso
      if (b * c < 0) attraversamenti.push([x0 + dx, y0 + (b / (b - c)) * dy]); // lato destro
      if (d * c < 0) attraversamenti.push([x0 + (d / (d - c)) * dx, y0 + dy]); // lato in alto
      if (a * d < 0) attraversamenti.push([x0, y0 + (a / (a - d)) * dy]); // lato sinistro

      // 2 attraversamenti: un trattino. 4 attraversamenti (caso raro): due trattini.
      for (let k = 0; k + 1 < attraversamenti.length; k += 2) {
        segmenti.push([...attraversamenti[k], ...attraversamenti[k + 1]] as Segmento);
      }
    }
  }
  return segmenti;
}

/** Sceglie i livelli da disegnare, a distanze uguali, scartando i valori estremi. */
export function scegliLivelli(valori: number[][], quanti: number): number[] {
  const tutti = valori.flat().filter(Number.isFinite).sort((p, q) => p - q);
  if (tutti.length === 0) return [];
  const basso = tutti[Math.floor(tutti.length * 0.03)];
  const alto = tutti[Math.ceil(tutti.length * 0.97) - 1];
  if (alto - basso < 1e-12) return [];
  const livelli: number[] = [];
  for (let k = 0; k < quanti; k++) livelli.push(basso + ((alto - basso) * (k + 0.5)) / quanti);
  return livelli;
}

// Colori dei punti notevoli, uguali nel grafico 3D e nella mappa
export const COLORI_PUNTI: Record<string, string> = {
  massimo: "#ffd866",
  minimo: "#7ee2a8",
  sella: "#ff9d8a",
  dubbio: "#f4f8ff",
  candidato: "#f4f8ff",
};

export const NOMI_PUNTI: Record<string, string> = {
  massimo: "Massimo",
  minimo: "Minimo",
  sella: "Sella",
  dubbio: "Caso dubbio",
  candidato: "Candidato",
};

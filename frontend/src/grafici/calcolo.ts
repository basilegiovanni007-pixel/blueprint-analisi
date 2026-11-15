// Strumenti di calcolo usati dai grafici: trasformano una formula in una funzione
// JavaScript veloce, e fanno qualche conto numerico (derivata, integrale).
import { compile } from "mathjs";

export type Funzione = (x: number) => number;

/**
 * Trasforma una formula (es. "a*sin(b*x)") in una funzione che il browser può calcolare
 * migliaia di volte al secondo. "parametri" contiene i valori delle altre lettere.
 * Dove la funzione non esiste (es. logaritmo di un numero negativo) restituisce NaN.
 */
export function compila(formula: string, variabile = "x", parametri: Record<string, number> = {}): Funzione {
  const programma = compile(formula);
  const valori: Record<string, number> = { ...parametri };
  return (x: number) => {
    valori[variabile] = x;
    try {
      const risultato = programma.evaluate(valori);
      // mathjs può restituire numeri complessi (es. radice di un negativo): per noi "non esiste"
      return typeof risultato === "number" && Number.isFinite(risultato) ? risultato : NaN;
    } catch {
      return NaN;
    }
  };
}

export type Funzione2 = (x: number, y: number) => number;

/** Come "compila", ma per una funzione di due variabili f(x, y). */
export function compila2(formula: string, variabili: [string, string] = ["x", "y"]): Funzione2 {
  const programma = compile(formula);
  const valori: Record<string, number> = {};
  return (x: number, y: number) => {
    valori[variabili[0]] = x;
    valori[variabili[1]] = y;
    try {
      const risultato = programma.evaluate(valori);
      return typeof risultato === "number" && Number.isFinite(risultato) ? risultato : NaN;
    } catch {
      return NaN;
    }
  };
}

/** Derivata numerica: pendenza calcolata su un intervallo piccolissimo attorno a x. */
export function derivataNumerica(f: Funzione, x: number): number {
  const h = 1e-5;
  return (f(x + h) - f(x - h)) / (2 * h);
}

/** Integrale numerico preciso (metodo di Simpson), usato come valore di confronto. */
export function integraleNumerico(f: Funzione, a: number, b: number, intervalli = 2000): number {
  const passo = (b - a) / intervalli;
  let somma = f(a) + f(b);
  for (let i = 1; i < intervalli; i++) {
    somma += f(a + i * passo) * (i % 2 === 0 ? 2 : 4);
  }
  return (somma * passo) / 3;
}

/** Scrive un numero all'italiana, con la virgola e al massimo 4 cifre significative. */
export function formatta(numero: number, cifre = 4): string {
  if (!Number.isFinite(numero)) return "—";
  if (Math.abs(numero) < 1e-10) return "0";
  return String(parseFloat(numero.toPrecision(cifre))).replace(".", ",");
}

/** Calcola una costante scritta dallo studente, es. "pi/2" o "2*e". NaN se non è valida. */
export function leggiNumero(testo: string): number {
  try {
    const valore = compile(testo.replace(",", ".").replace("π", "pi")).evaluate({});
    return typeof valore === "number" && Number.isFinite(valore) ? valore : NaN;
  } catch {
    return NaN;
  }
}

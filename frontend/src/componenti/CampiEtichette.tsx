// I campi per etichettare un documento: argomento, fonte e data.
// Usati sia quando si carica un file sia quando si modifica un documento esistente.
import type { Etichette, Opzioni } from "../api/client";

type Props = {
  opzioni: Opzioni;
  valori: Etichette;
  onCambia: (nuovi: Etichette) => void; // chiamata a ogni modifica di un campo
  conAuto?: boolean; // aggiunge la scelta "Riconosci in automatico" (solo al caricamento)
};

// Valore dell'argomento quando lo deve riconoscere l'app
export const AUTOMATICO = "auto";

export default function CampiEtichette({ opzioni, valori, onCambia, conAuto = false }: Props) {
  return (
    <div className="campi">
      <label className="campo">
        <span>Argomento</span>
        <select value={valori.argomento} onChange={(e) => onCambia({ ...valori, argomento: e.target.value })}>
          {conAuto && <option value={AUTOMATICO}>Riconosci in automatico</option>}
          {/* Gli argomenti sono raggruppati per corso: Analisi I e Analisi II */}
          {Object.entries(opzioni.argomenti).map(([corso, argomenti]) => (
            <optgroup key={corso} label={corso}>
              {argomenti.map((argomento) => (
                <option key={argomento}>{argomento}</option>
              ))}
            </optgroup>
          ))}
        </select>
      </label>

      <label className="campo">
        <span>Fonte</span>
        <select value={valori.fonte} onChange={(e) => onCambia({ ...valori, fonte: e.target.value })}>
          {opzioni.fonti.map((fonte) => (
            <option key={fonte}>{fonte}</option>
          ))}
        </select>
      </label>

      <label className="campo">
        <span>Data</span>
        <input type="date" value={valori.data} onChange={(e) => onCambia({ ...valori, data: e.target.value })} />
      </label>
    </div>
  );
}

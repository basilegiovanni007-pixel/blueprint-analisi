// Un cursore (slider) con etichetta e valore, usato in tutti gli strumenti del laboratorio.
import { formatta } from "./calcolo";

type Props = {
  etichetta: string;
  valore: number;
  min: number;
  max: number;
  passo: number;
  onCambia: (valore: number) => void;
};

export default function Cursore({ etichetta, valore, min, max, passo, onCambia }: Props) {
  return (
    <label className="cursore">
      <span className="cursore-testa">
        <span>{etichetta}</span>
        <output>{formatta(valore)}</output>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        step={passo}
        value={valore}
        onChange={(e) => onCambia(Number(e.target.value))}
      />
    </label>
  );
}

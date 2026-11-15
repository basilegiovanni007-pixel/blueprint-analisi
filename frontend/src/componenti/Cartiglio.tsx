// Il "cartiglio": il riquadro in basso a destra dei disegni tecnici.
// Normalmente mostra il nome della pagina; quando c'è una soluzione aperta mostra
// il nome dell'esercizio, il suo argomento e la data in cui è stato risolto.
import { useDatiCartiglio } from "./ContestoCartiglio";

export default function Cartiglio({ pagina }: { pagina: string }) {
  const dati = useDatiCartiglio();
  const quando = dati?.data ? new Date(dati.data) : new Date();
  const data = quando.toLocaleDateString("it-IT"); // es. 14/11/2026

  return (
    <aside className="cartiglio" aria-label="Cartiglio">
      <div className="cartiglio-cella larga">
        <small>Tavola</small>
        {dati?.titolo ?? pagina}
      </div>
      {dati?.esercizio && (
        <div className="cartiglio-cella larga cartiglio-esercizio">
          <small>Esercizio</small>
          {dati.esercizio}
        </div>
      )}
      <div className="cartiglio-cella">
        <small>Argomento</small>
        {dati?.argomento ?? "Analisi I e II"}
      </div>
      <div className="cartiglio-cella">
        <small>Data</small>
        {data}
      </div>
    </aside>
  );
}

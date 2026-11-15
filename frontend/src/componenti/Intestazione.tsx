// Titolo di pagina con etichetta, descrizione e una "linea di quota" decorativa.

type Props = {
  etichetta: string; // piccola scritta sopra il titolo, es. "Tavola 01"
  titolo: string;
  descrizione: string;
};

export default function Intestazione({ etichetta, titolo, descrizione }: Props) {
  return (
    // Nel PDF l'intestazione della pagina non serve: c'è quella dell'esercizio
    <header className="intestazione non-stampare">
      <div className="intestazione-etichetta">{etichetta}</div>
      <h1>{titolo}</h1>
      <p>{descrizione}</p>
      <div className="quota" aria-hidden="true">
        <div className="quota-linea" />
      </div>
    </header>
  );
}

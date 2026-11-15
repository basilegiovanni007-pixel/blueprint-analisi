// Un riquadro con i quattro angoli "a squadra", usato in tutte le pagine.
import type { ReactNode } from "react";

type Props = {
  titolo?: string;
  largo?: boolean; // se true occupa tutta la larghezza della griglia
  children: ReactNode; // il contenuto messo dentro al pannello
  classe?: string; // classi CSS aggiuntive, es. "non-stampare"
};

export default function Pannello({ titolo, largo, children, classe }: Props) {
  return (
    <section className={"pannello" + (largo ? " pannello-largo" : "") + (classe ? " " + classe : "")}>
      <span className="pannello-angolo as" />
      <span className="pannello-angolo ad" />
      <span className="pannello-angolo bs" />
      <span className="pannello-angolo bd" />
      {titolo && <h2 className="pannello-titolo">{titolo}</h2>}
      {children}
    </section>
  );
}

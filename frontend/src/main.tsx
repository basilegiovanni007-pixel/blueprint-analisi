// Punto di partenza del frontend: carica font, stili e avvia React.
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

// Font installati in locale (funzionano anche senza internet)
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "@fontsource/ibm-plex-mono/600.css";
import "@fontsource/ibm-plex-sans/400.css";
import "@fontsource/ibm-plex-sans/500.css";

// Stile delle formule KaTeX e tema blueprint
import "katex/dist/katex.min.css";
import "./tema/tema.css";

import App from "./App";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {/* BrowserRouter permette di avere più "pagine" (Risolutore, Magazzino...) */}
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
);

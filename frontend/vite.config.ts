import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Configurazione di Vite, lo strumento che avvia il frontend in sviluppo.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // "Proxy": quando il frontend chiama un indirizzo che inizia con /api,
    // Vite inoltra la richiesta al backend Python su localhost:8000.
    // Così nel codice scriviamo solo "/api/..." senza pensare alle porte.
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
});

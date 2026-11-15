"""Test delle pagine del frontend servite dal backend (versione installata)."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.frontend_statico import monta_frontend


def test_frontend_servito_dal_backend(tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>pagina principale</html>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path / "segreto.txt").write_text("non deve uscire", encoding="utf-8")

    app = FastAPI()

    @app.get("/api/prova")
    def prova():
        return {"ok": True}

    monta_frontend(app, dist)
    client = TestClient(app)

    assert client.get("/").text == "<html>pagina principale</html>"
    assert client.get("/assets/app.js").text == "console.log(1)"
    # Gli indirizzi gestiti da React ricevono index.html
    assert "pagina principale" in client.get("/storico/12").text
    # Gli sportelli /api hanno la precedenza; quelli inesistenti danno 404, non la pagina
    assert client.get("/api/prova").json() == {"ok": True}
    assert client.get("/api/inesistente").status_code == 404
    # Non si può uscire dalla cartella del frontend
    assert "non deve uscire" not in client.get("/../segreto.txt").text
    assert "non deve uscire" not in client.get("/assets/..%2F..%2Fsegreto.txt").text

"""
Preparazione comune a tutti i test.

I test NON devono toccare i dati veri dello studente: per questo, prima di caricare
l'app, diciamo al backend di usare una cartella temporanea e un embedding "finto"
(veloce, senza scaricare il modello linguistico).
"""

import os
import tempfile

os.environ["BLUEPRINT_DATI"] = tempfile.mkdtemp(prefix="blueprint-test-")
os.environ["BLUEPRINT_EMBEDDING"] = "finto"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    """Un finto browser che parla col backend. Il 'with' esegue anche l'avvio del server."""
    with TestClient(app) as c:
        yield c

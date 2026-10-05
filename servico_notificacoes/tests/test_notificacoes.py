from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_saude():
    assert client.get("/saude").status_code == 200


def test_criar_notificacao_com_dados_invalidos():
    assert client.post("/notificacoes", json={"tipo": "x"}).status_code == 422


def test_criar_notificacao(monkeypatch):
    salva = {"id": 1, "usuario_id": 1, "tipo": "emprestimo", "mensagem": "Oi"}
    monkeypatch.setattr("app.main.executar", lambda *a, **k: salva)
    dados = {"usuario_id": 1, "tipo": "emprestimo", "mensagem": "Oi"}
    resposta = client.post("/notificacoes", json=dados)
    assert resposta.status_code == 201


def test_listar_notificacoes_exige_login():
    assert client.get("/notificacoes").status_code == 401

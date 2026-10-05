from datetime import datetime, timedelta, timezone
import jwt
from fastapi.testclient import TestClient
from app.main import app
from app.seguranca import ALGORITMO, SEGREDO

client = TestClient(app)


def cabecalho_com_token():
    validade = datetime.now(timezone.utc) + timedelta(minutes=5)
    token = jwt.encode(
        {"sub": "1", "email": "a@a.com", "exp": validade}, SEGREDO, algorithm=ALGORITMO
    )
    return {"Authorization": f"Bearer {token}"}


def test_saude():
    assert client.get("/saude").status_code == 200


def test_cadastro_de_livro_exige_login():
    dados = {"titulo": "Dom Casmurro", "autor": "Machado de Assis"}
    assert client.post("/livros", json=dados).status_code == 401


def test_cadastro_com_titulo_vazio():
    dados = {"titulo": "", "autor": "Machado de Assis"}
    resposta = client.post("/livros", json=dados, headers=cabecalho_com_token())
    assert resposta.status_code == 422


def test_reservar_exige_login():
    assert client.post("/livros/1/reservar").status_code == 401


def test_listar_livros(monkeypatch):
    livro = {"id": 1, "titulo": "Dom Casmurro", "autor": "Machado", "ano": 1899}
    livros = [dict(livro, disponivel=True)]
    # troca o acesso ao banco por uma função falsa (teste unitário, sem banco)
    monkeypatch.setattr("app.main.executar", lambda *args, **kwargs: livros)
    resposta = client.get("/livros")
    assert resposta.status_code == 200
    assert resposta.json()[0]["titulo"] == "Dom Casmurro"


def test_livro_inexistente(monkeypatch):
    monkeypatch.setattr("app.main.executar", lambda *args, **kwargs: None)
    assert client.get("/livros/999").status_code == 404


def test_reservar_livro_indisponivel(monkeypatch):
    respostas = iter([None, {"id": 1}])
    monkeypatch.setattr("app.main.executar", lambda *args, **kwargs: next(respostas))
    resposta = client.post("/livros/1/reservar", headers=cabecalho_com_token())
    assert resposta.status_code == 409

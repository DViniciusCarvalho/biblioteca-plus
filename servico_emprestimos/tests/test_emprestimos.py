from datetime import datetime, timedelta, timezone
import jwt
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.main import app
from app.seguranca import ALGORITMO, SEGREDO

client = TestClient(app)


def cabecalho_com_token(usuario_id=1):
    validade = datetime.now(timezone.utc) + timedelta(minutes=5)
    token = jwt.encode(
        {"sub": str(usuario_id), "email": "a@a.com", "exp": validade},
        SEGREDO,
        algorithm=ALGORITMO,
    )
    return {"Authorization": f"Bearer {token}"}


def test_saude():
    assert client.get("/saude").status_code == 200


def test_emprestimo_exige_login():  # RN01
    assert client.post("/emprestimos", json={"livro_id": 1}).status_code == 401


def test_emprestimo_sem_livro_id():
    resposta = client.post("/emprestimos", json={}, headers=cabecalho_com_token())
    assert resposta.status_code == 422


def test_limite_de_emprestimos(monkeypatch):  # RN03
    monkeypatch.setattr("app.main.executar", lambda *a, **k: {"total": 3})
    resposta = client.post(
        "/emprestimos", json={"livro_id": 1}, headers=cabecalho_com_token()
    )
    assert resposta.status_code == 409


def test_livro_indisponivel(monkeypatch):  # RN02
    monkeypatch.setattr("app.main.executar", lambda *a, **k: {"total": 0})

    def livro_ocupado(livro_id, token):
        raise HTTPException(status_code=409, detail="Livro indisponível")

    monkeypatch.setattr("app.main.reservar_livro", livro_ocupado)
    resposta = client.post(
        "/emprestimos", json={"livro_id": 1}, headers=cabecalho_com_token()
    )
    assert resposta.status_code == 409


def test_servico_de_livros_fora_do_ar(monkeypatch):  # tolerância a falhas
    monkeypatch.setattr("app.main.executar", lambda *a, **k: {"total": 0})

    def sem_resposta(livro_id, token):
        raise HTTPException(status_code=503, detail="Serviço de livros indisponível")

    monkeypatch.setattr("app.main.reservar_livro", sem_resposta)
    resposta = client.post(
        "/emprestimos", json={"livro_id": 1}, headers=cabecalho_com_token()
    )
    assert resposta.status_code == 503


def test_emprestimo_de_outro_usuario(monkeypatch):
    emprestimo = {"id": 5, "usuario_id": 99, "status": "ativo"}
    monkeypatch.setattr("app.main.executar", lambda *a, **k: emprestimo)
    resposta = client.get("/emprestimos/5", headers=cabecalho_com_token(usuario_id=1))
    assert resposta.status_code == 403

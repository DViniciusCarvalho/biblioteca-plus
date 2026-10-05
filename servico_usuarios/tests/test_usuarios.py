from fastapi.testclient import TestClient
from app.main import app
from app.seguranca import criar_token, gerar_hash_senha, verificar_senha

client = TestClient(app)


def test_saude():
    resposta = client.get("/saude")
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "ok"


def test_senha_correta_e_incorreta():
    senha_hash = gerar_hash_senha("Senha123")
    assert verificar_senha("Senha123", senha_hash) is True
    assert verificar_senha("outra", senha_hash) is False


def test_hash_nao_guarda_senha_em_texto_puro():
    assert "Senha123" not in gerar_hash_senha("Senha123")


def test_cadastro_com_email_invalido():
    dados = {"nome": "João da Silva", "email": "email-invalido", "senha": "Senha123"}
    assert client.post("/usuarios", json=dados).status_code == 422


def test_cadastro_sem_nome():
    dados = {"email": "joao@example.com", "senha": "Senha123"}
    assert client.post("/usuarios", json=dados).status_code == 422


def test_cadastro_com_senha_curta():
    dados = {"nome": "João", "email": "joao@example.com", "senha": "123"}
    assert client.post("/usuarios", json=dados).status_code == 422


def test_consulta_sem_token():
    assert client.get("/usuarios/me").status_code == 401


def test_consulta_com_token_invalido():
    cabecalho = {"Authorization": "Bearer token-falso"}
    assert client.get("/usuarios/me", headers=cabecalho).status_code == 401


def test_nao_pode_ver_dados_de_outro_usuario():
    token = criar_token(1, "joao@example.com")
    cabecalho = {"Authorization": f"Bearer {token}"}
    assert client.get("/usuarios/2", headers=cabecalho).status_code == 403

"""Teste de integração: percorre o fluxo completo pelo gateway.

Precisa do sistema rodando (docker compose up -d --build).
Execute na raiz do projeto:  python -m pytest testes -v
"""

import os
import uuid

import requests

BASE = os.getenv("URL_GATEWAY", "http://localhost:8080")


def criar_usuario_e_logar():
    email = f"teste_{uuid.uuid4().hex[:8]}@example.com"
    dados = {"nome": "João da Silva", "email": email, "senha": "Senha123"}
    cadastro = requests.post(f"{BASE}/usuarios", json=dados, timeout=10)
    assert cadastro.status_code == 201  # RT01
    login = requests.post(
        f"{BASE}/login", json={"email": email, "senha": "Senha123"}, timeout=10
    )
    assert login.status_code == 200
    return email, {"Authorization": f"Bearer {login.json()['access_token']}"}


def criar_livro(cabecalho):
    dados = {"titulo": "Livro de Teste", "autor": "Autor de Teste", "ano": 2020}
    resposta = requests.post(
        f"{BASE}/livros", json=dados, headers=cabecalho, timeout=10
    )
    assert resposta.status_code == 201
    return resposta.json()["id"]


def livro_esta_disponivel(livro_id):
    return requests.get(f"{BASE}/livros/{livro_id}", timeout=10).json()["disponivel"]


def test_gateway_no_ar():
    assert requests.get(f"{BASE}/saude", timeout=10).status_code == 200


def test_email_duplicado():
    email, _ = criar_usuario_e_logar()
    dados = {"nome": "Outro", "email": email, "senha": "Senha123"}
    assert requests.post(f"{BASE}/usuarios", json=dados, timeout=10).status_code == 409


def test_emprestimo_sem_login():  # RN01
    resposta = requests.post(f"{BASE}/emprestimos", json={"livro_id": 1}, timeout=10)
    assert resposta.status_code == 401


def test_fluxo_completo_de_emprestimo():
    _, cabecalho = criar_usuario_e_logar()
    livro_id = criar_livro(cabecalho)
    assert livro_esta_disponivel(livro_id) is True

    # empréstimo
    resposta = requests.post(
        f"{BASE}/emprestimos",
        json={"livro_id": livro_id},
        headers=cabecalho,
        timeout=10,
    )
    assert resposta.status_code == 201
    emprestimo_id = resposta.json()["id"]
    assert livro_esta_disponivel(livro_id) is False  # RN04

    # consulta dos empréstimos do usuário (RF10 / RF13)
    lista = requests.get(f"{BASE}/emprestimos", headers=cabecalho, timeout=10)
    assert lista.status_code == 200
    assert any(e["id"] == emprestimo_id for e in lista.json())

    # segundo empréstimo do mesmo livro deve ser bloqueado (RN02)
    _, outro_cabecalho = criar_usuario_e_logar()
    repetido = requests.post(
        f"{BASE}/emprestimos",
        json={"livro_id": livro_id},
        headers=outro_cabecalho,
        timeout=10,
    )
    assert repetido.status_code == 409

    # devolução
    devolucao = requests.post(
        f"{BASE}/emprestimos/{emprestimo_id}/devolucao", headers=cabecalho, timeout=10
    )
    assert devolucao.status_code == 200
    assert devolucao.json()["status"] == "devolvido"
    assert livro_esta_disponivel(livro_id) is True

    # notificações geradas (empréstimo + devolução)
    notificacoes = requests.get(f"{BASE}/notificacoes", headers=cabecalho, timeout=10)
    assert len(notificacoes.json()) >= 2


def test_nao_pode_criar_notificacao_por_fora():
    dados = {"usuario_id": 1, "tipo": "x", "mensagem": "invasão"}
    resposta = requests.post(f"{BASE}/notificacoes", json=dados, timeout=10)
    assert resposta.status_code == 403  # bloqueado pelo gateway


def test_login_com_senha_errada():
    email, _ = criar_usuario_e_logar()
    resposta = requests.post(
        f"{BASE}/login", json={"email": email, "senha": "senha-errada"}, timeout=10
    )
    assert resposta.status_code == 401


def test_nao_pode_reservar_livro_por_fora():
    _, cabecalho = criar_usuario_e_logar()
    resposta = requests.post(f"{BASE}/livros/1/reservar", headers=cabecalho, timeout=10)
    assert resposta.status_code == 403  # rota interna, bloqueada pelo gateway

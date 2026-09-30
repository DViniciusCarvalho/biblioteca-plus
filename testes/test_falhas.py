"""Testes de falhas: derrubam um serviço de propósito e veem como o sistema reage.

Precisam do sistema rodando com Docker (docker compose up -d --build).
Execute na raiz do projeto:  python -m pytest testes/test_falhas.py -v -s

Sem Docker instalado, os testes são ignorados.
"""

import os
import shutil
import subprocess
import time

import pytest
import requests

from test_integracao import BASE, criar_livro, criar_usuario_e_logar

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

pytestmark = pytest.mark.skipif(
    shutil.which("docker") is None, reason="Docker não encontrado"
)


def docker(*argumentos):
    subprocess.run(["docker", "compose", *argumentos], cwd=RAIZ, check=True)


def esperar_no_ar(url, tentativas=30):
    """Espera o endereço responder 200 (até ~60 segundos)."""
    for _ in range(tentativas):
        try:
            if requests.get(url, timeout=3).status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(2)
    return False


def religar(servico):
    docker("start", servico)
    # o gateway guarda o endereço antigo do serviço; reiniciar garante o novo
    docker("restart", "gateway")
    assert esperar_no_ar(f"{BASE}/livros"), "sistema não voltou depois da falha"


def test_emprestimo_com_servico_de_livros_fora_do_ar():
    _, cabecalho = criar_usuario_e_logar()
    livro_id = criar_livro(cabecalho)
    docker("stop", "livros")
    try:
        resposta = requests.post(
            f"{BASE}/emprestimos",
            json={"livro_id": livro_id},
            headers=cabecalho,
            timeout=15,
        )
        assert resposta.status_code == 503  # falha tratada, sem erro 500
    finally:
        religar("livros")


def test_emprestimo_continua_sem_servico_de_notificacoes():
    _, cabecalho = criar_usuario_e_logar()
    livro_id = criar_livro(cabecalho)
    docker("stop", "notificacoes")
    try:
        resposta = requests.post(
            f"{BASE}/emprestimos",
            json={"livro_id": livro_id},
            headers=cabecalho,
            timeout=15,
        )
        assert resposta.status_code == 201  # notificação é opcional
        emprestimo_id = resposta.json()["id"]
    finally:
        religar("notificacoes")
    # limpeza: devolve o livro
    url = f"{BASE}/emprestimos/{emprestimo_id}/devolucao"
    assert requests.post(url, headers=cabecalho, timeout=10).status_code == 200


def test_banco_de_dados_fora_do_ar():
    docker("stop", "banco")
    try:
        resposta = requests.get(f"{BASE}/livros", timeout=20)
        assert resposta.status_code == 503
    finally:
        docker("start", "banco")
        # os serviços reconectam sozinhos (abrem uma conexão nova a cada pedido)
        assert esperar_no_ar(f"{BASE}/livros"), "sistema não voltou depois da falha"

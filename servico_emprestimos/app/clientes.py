import logging
import os
import requests
from fastapi import HTTPException

URL_LIVROS = os.getenv("URL_LIVROS", "http://localhost:8002")
URL_NOTIFICACOES = os.getenv("URL_NOTIFICACOES", "http://localhost:8004")
TIMEOUT = 3

log = logging.getLogger("emprestimos")


def _chamar_livros(caminho, token):
    try:
        return requests.post(
            f"{URL_LIVROS}{caminho}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=TIMEOUT,
        )
    except requests.RequestException:
        log.error("Serviço de livros não respondeu (%s)", caminho)
        raise HTTPException(status_code=503, detail="Serviço de livros indisponível")


def reservar_livro(livro_id, token):
    resposta = _chamar_livros(f"/livros/{livro_id}/reservar", token)
    if resposta.status_code == 404:
        raise HTTPException(status_code=404, detail="Livro não encontrado")
    if resposta.status_code == 409:
        raise HTTPException(status_code=409, detail="Livro indisponível")
    if resposta.status_code != 200:
        raise HTTPException(status_code=502, detail="Erro no serviço de livros")
    return resposta.json()


def liberar_livro(livro_id, token, ignorar_erro=False):
    try:
        resposta = _chamar_livros(f"/livros/{livro_id}/liberar", token)
        if resposta.status_code != 200:
            raise HTTPException(status_code=502, detail="Erro no serviço de livros")
    except HTTPException:
        if ignorar_erro:
            log.error("Não foi possível liberar o livro %s", livro_id)
        else:
            raise


def notificar(usuario_id, tipo, mensagem):
    try:
        requests.post(
            f"{URL_NOTIFICACOES}/notificacoes",
            json={"usuario_id": usuario_id, "tipo": tipo, "mensagem": mensagem},
            timeout=TIMEOUT,
        )
    except requests.RequestException:
        log.warning("Notificação não enviada (serviço fora do ar)")

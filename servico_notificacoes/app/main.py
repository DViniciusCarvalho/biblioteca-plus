import logging

import psycopg2
from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, Field

from app.database import executar
from app.seguranca import usuario_atual

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [notificacoes] %(levelname)s %(message)s"
)
log = logging.getLogger("notificacoes")

app = FastAPI(title="Biblioteca+ - Serviço de Notificações")
Instrumentator().instrument(app).expose(app) 


class NovaNotificacao(BaseModel):
    usuario_id: int
    tipo: str = Field(min_length=1, max_length=30)
    mensagem: str = Field(min_length=1, max_length=500)


@app.exception_handler(psycopg2.OperationalError)
def banco_indisponivel(request, erro):
    log.error("Banco de dados indisponível: %s", erro)
    return JSONResponse(status_code=503, content={"detail": "Banco indisponível"})


@app.get("/saude")
def saude():
    return {"status": "ok", "servico": "notificacoes"}


@app.post("/notificacoes", status_code=201)
def criar(dados: NovaNotificacao):
    notificacao = executar(
        "INSERT INTO notificacoes (usuario_id, tipo, mensagem) VALUES (%s, %s, %s) "
        "RETURNING id, usuario_id, tipo, mensagem, criado_em",
        (dados.usuario_id, dados.tipo, dados.mensagem),
        "um",
    )
    log.info("[SIMULAÇÃO DE ENVIO] usuario=%s: %s", dados.usuario_id, dados.mensagem)
    return notificacao


@app.get("/notificacoes")
def listar_minhas(atual: dict = Depends(usuario_atual)):
    return executar(
        "SELECT id, tipo, mensagem, criado_em FROM notificacoes "
        "WHERE usuario_id = %s ORDER BY id DESC",
        (atual["id"],),
        "todos",
    )

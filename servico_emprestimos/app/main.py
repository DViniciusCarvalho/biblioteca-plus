import logging
import os

import psycopg2
import psycopg2.errors
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel

from app.clientes import liberar_livro, notificar, reservar_livro
from app.database import executar
from app.seguranca import usuario_atual

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [emprestimos] %(levelname)s %(message)s"
)
log = logging.getLogger("emprestimos")

app = FastAPI(title="Biblioteca+ - Serviço de Empréstimos")
Instrumentator().instrument(app).expose(app)  # cria a rota /metrics

MAX_EMPRESTIMOS = int(os.getenv("MAX_EMPRESTIMOS", "3"))  # RN03
DIAS_DE_EMPRESTIMO = 14

COLUNAS = (
    "id, usuario_id, livro_id, status, data_emprestimo, "
    "data_prevista_devolucao, data_devolucao"
)


class NovoEmprestimo(BaseModel):
    livro_id: int


@app.exception_handler(psycopg2.OperationalError)
def banco_indisponivel(request, erro):
    log.error("Banco de dados indisponível: %s", erro)
    return JSONResponse(status_code=503, content={"detail": "Banco indisponível"})


@app.get("/saude")
def saude():
    return {"status": "ok", "servico": "emprestimos"}


@app.post("/emprestimos", status_code=201)
def criar(dados: NovoEmprestimo, atual: dict = Depends(usuario_atual)):
    ativos = executar(
        "SELECT COUNT(*) AS total FROM emprestimos "
        "WHERE usuario_id = %s AND status = 'ativo'",
        (atual["id"],),
        "um",
    )["total"]
    if ativos >= MAX_EMPRESTIMOS:
        raise HTTPException(
            status_code=409,
            detail=f"Limite de {MAX_EMPRESTIMOS} empréstimos ativos atingido",
        )

    livro = reservar_livro(dados.livro_id, atual["token"])

    try:
        emprestimo = executar(
            "INSERT INTO emprestimos (usuario_id, livro_id, data_prevista_devolucao) "
            f"VALUES (%s, %s, NOW() + %s * INTERVAL '1 day') RETURNING {COLUNAS}",
            (atual["id"], dados.livro_id, DIAS_DE_EMPRESTIMO),
            "um",
        )
    except Exception:
        liberar_livro(dados.livro_id, atual["token"], ignorar_erro=True)
        raise

    log.info("Empréstimo criado id=%s usuario=%s", emprestimo["id"], atual["id"])
    prazo = emprestimo["data_prevista_devolucao"].strftime("%d/%m/%Y")
    notificar(
        atual["id"],
        "emprestimo",
        f'Empréstimo #{emprestimo["id"]} do livro "{livro["titulo"]}" confirmado. '
        f"Devolva até {prazo}.",
    )
    emprestimo["titulo_livro"] = livro["titulo"]
    return emprestimo


@app.get("/emprestimos")
def listar(status: str | None = None, atual: dict = Depends(usuario_atual)):
    sql = f"SELECT {COLUNAS} FROM emprestimos WHERE usuario_id = %s"
    parametros = [atual["id"]]
    if status:
        sql += " AND status = %s"
        parametros.append(status)
    sql += " ORDER BY id DESC"
    return executar(sql, parametros, "todos")


def buscar_do_usuario(emprestimo_id, usuario_id):
    emprestimo = executar(
        f"SELECT {COLUNAS}, (data_emprestimo > NOW() - INTERVAL '1 day') AS pode_cancelar "
        "FROM emprestimos WHERE id = %s",
        (emprestimo_id,),
        "um",
    )
    if emprestimo is None:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado")
    if emprestimo["usuario_id"] != usuario_id:
        raise HTTPException(status_code=403, detail="Este empréstimo não é seu")
    return emprestimo


@app.get("/emprestimos/{emprestimo_id}")
def consultar(emprestimo_id: int, atual: dict = Depends(usuario_atual)):
    return buscar_do_usuario(emprestimo_id, atual["id"])


def encerrar(emprestimo_id, novo_status, tipo_notificacao, mensagem, atual):
    emprestimo = buscar_do_usuario(emprestimo_id, atual["id"])
    if emprestimo["status"] != "ativo":
        raise HTTPException(status_code=409, detail="Empréstimo já encerrado")
    if novo_status == "cancelado" and not emprestimo["pode_cancelar"]:
        raise HTTPException(
            status_code=409, detail="Só é possível cancelar em até 24 horas"
        )

    liberar_livro(emprestimo["livro_id"], atual["token"])  # RN04
    fechado = executar(
        "UPDATE emprestimos SET status = %s, data_devolucao = NOW() "
        f"WHERE id = %s AND status = 'ativo' RETURNING {COLUNAS}",
        (novo_status, emprestimo_id),
        "um",
    )
    if fechado is None:
        raise HTTPException(status_code=409, detail="Empréstimo já encerrado")
    log.info("Empréstimo %s id=%s", novo_status, emprestimo_id)
    notificar(atual["id"], tipo_notificacao, mensagem)
    return fechado


@app.post("/emprestimos/{emprestimo_id}/devolucao")
def devolver(emprestimo_id: int, atual: dict = Depends(usuario_atual)):
    return encerrar(
        emprestimo_id,
        "devolvido",
        "devolucao",
        f"Devolução do empréstimo #{emprestimo_id} registrada. Obrigado!",
        atual,
    )


@app.post("/emprestimos/{emprestimo_id}/cancelar")
def cancelar(emprestimo_id: int, atual: dict = Depends(usuario_atual)):
    return encerrar(
        emprestimo_id,
        "cancelado",
        "cancelamento",
        f"Empréstimo #{emprestimo_id} cancelado.",
        atual,
    )


@app.post("/emprestimos/lembretes/gerar")
def gerar_lembretes(atual: dict = Depends(usuario_atual)):
    vencendo = executar(
        "SELECT id, data_prevista_devolucao FROM emprestimos "
        "WHERE usuario_id = %s AND status = 'ativo' "
        "AND data_prevista_devolucao <= NOW() + INTERVAL '2 days'",
        (atual["id"],),
        "todos",
    )
    for e in vencendo:
        prazo = e["data_prevista_devolucao"].strftime("%d/%m/%Y")
        notificar(
            atual["id"],
            "aviso_devolucao",
            f"O empréstimo #{e['id']} vence em {prazo}. Não esqueça de devolver!",
        )
    return {"lembretes_enviados": len(vencendo)}

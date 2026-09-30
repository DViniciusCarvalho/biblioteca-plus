import logging
import psycopg2
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, Field

from app.database import executar
from app.seguranca import usuario_atual

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [livros] %(levelname)s %(message)s"
)
log = logging.getLogger("livros")

app = FastAPI(title="Biblioteca+ - Serviço de Livros")
Instrumentator().instrument(app).expose(app)

COLUNAS = "id, titulo, autor, ano, disponivel"


class LivroCadastro(BaseModel):
    titulo: str = Field(min_length=1, max_length=200)
    autor: str = Field(min_length=1, max_length=150)
    ano: int | None = Field(default=None, ge=0, le=2100)


class LivroAtualizacao(BaseModel):
    titulo: str | None = Field(default=None, min_length=1, max_length=200)
    autor: str | None = Field(default=None, min_length=1, max_length=150)
    ano: int | None = Field(default=None, ge=0, le=2100)


@app.exception_handler(psycopg2.OperationalError)
def banco_indisponivel(request, erro):
    log.error("Banco de dados indisponível: %s", erro)
    return JSONResponse(status_code=503, content={"detail": "Banco indisponível"})


@app.get("/saude")
def saude():
    return {"status": "ok", "servico": "livros"}


@app.post("/livros", status_code=201)
def cadastrar(dados: LivroCadastro, atual: dict = Depends(usuario_atual)):
    livro = executar(
        f"INSERT INTO livros (titulo, autor, ano) VALUES (%s, %s, %s) RETURNING {COLUNAS}",
        (dados.titulo, dados.autor, dados.ano),
        "um",
    )
    log.info("Livro cadastrado id=%s por usuario=%s", livro["id"], atual["id"])
    return livro


@app.get("/livros")
def listar(
    titulo: str | None = None,
    autor: str | None = None,
    somente_disponiveis: bool = False,
):
    sql = f"SELECT {COLUNAS} FROM livros WHERE 1 = 1"
    parametros = []
    if titulo:
        sql += " AND titulo ILIKE %s"
        parametros.append(f"%{titulo}%")
    if autor:
        sql += " AND autor ILIKE %s"
        parametros.append(f"%{autor}%")
    if somente_disponiveis:
        sql += " AND disponivel = TRUE"
    sql += " ORDER BY titulo"
    return executar(sql, parametros, "todos")


@app.get("/livros/{livro_id}")
def consultar(livro_id: int):
    livro = executar(f"SELECT {COLUNAS} FROM livros WHERE id = %s", (livro_id,), "um")
    if livro is None:
        raise HTTPException(status_code=404, detail="Livro não encontrado")
    return livro


@app.put("/livros/{livro_id}")
def atualizar(
    livro_id: int, dados: LivroAtualizacao, atual: dict = Depends(usuario_atual)
):
    campos = []
    valores = []
    if dados.titulo:
        campos.append("titulo = %s")
        valores.append(dados.titulo)
    if dados.autor:
        campos.append("autor = %s")
        valores.append(dados.autor)
    if dados.ano is not None:
        campos.append("ano = %s")
        valores.append(dados.ano)
    if not campos:
        raise HTTPException(status_code=400, detail="Nenhum dado para atualizar")

    valores.append(livro_id)
    livro = executar(
        f"UPDATE livros SET {', '.join(campos)} WHERE id = %s RETURNING {COLUNAS}",
        valores,
        "um",
    )
    if livro is None:
        raise HTTPException(status_code=404, detail="Livro não encontrado")
    log.info("Livro atualizado id=%s", livro_id)
    return livro


@app.post("/livros/{livro_id}/reservar")
def reservar(livro_id: int, atual: dict = Depends(usuario_atual)):
    livro = executar(
        "UPDATE livros SET disponivel = FALSE "
        f"WHERE id = %s AND disponivel = TRUE RETURNING {COLUNAS}",
        (livro_id,),
        "um",
    )
    if livro is None:
        existe = executar("SELECT id FROM livros WHERE id = %s", (livro_id,), "um")
        if existe is None:
            raise HTTPException(status_code=404, detail="Livro não encontrado")
        raise HTTPException(status_code=409, detail="Livro indisponível")
    log.info("Livro reservado id=%s", livro_id)
    return livro


@app.post("/livros/{livro_id}/liberar")
def liberar(livro_id: int, atual: dict = Depends(usuario_atual)):
    livro = executar(
        f"UPDATE livros SET disponivel = TRUE WHERE id = %s RETURNING {COLUNAS}",
        (livro_id,),
        "um",
    )
    if livro is None:
        raise HTTPException(status_code=404, detail="Livro não encontrado")
    log.info("Livro liberado id=%s", livro_id)
    return livro

"""Serviço de Usuários: cadastro, login e consulta de dados."""

import logging

import psycopg2
import psycopg2.errors
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, EmailStr, Field

from app.database import executar
from app.seguranca import (
    criar_token,
    gerar_hash_senha,
    usuario_atual,
    verificar_senha,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [usuarios] %(levelname)s %(message)s"
)
log = logging.getLogger("usuarios")

app = FastAPI(title="Biblioteca+ - Serviço de Usuários")
Instrumentator().instrument(app).expose(app)  # cria a rota /metrics


class UsuarioCadastro(BaseModel):
    nome: str = Field(min_length=2, max_length=100)
    email: EmailStr
    senha: str = Field(min_length=6, max_length=100)


class UsuarioAtualizacao(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=100)
    email: EmailStr | None = None
    senha: str | None = Field(default=None, min_length=6, max_length=100)


class Login(BaseModel):
    email: EmailStr
    senha: str


@app.exception_handler(psycopg2.OperationalError)
def banco_indisponivel(request, erro):
    log.error("Banco de dados indisponível: %s", erro)
    return JSONResponse(status_code=503, content={"detail": "Banco indisponível"})


@app.get("/saude")
def saude():
    return {"status": "ok", "servico": "usuarios"}


@app.post("/usuarios", status_code=201)
def cadastrar(dados: UsuarioCadastro):
    try:
        usuario = executar(
            "INSERT INTO usuarios (nome, email, senha_hash) VALUES (%s, %s, %s) "
            "RETURNING id, nome, email",
            (dados.nome, dados.email.lower(), gerar_hash_senha(dados.senha)),
            "um",
        )
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(status_code=409, detail="E-mail já cadastrado")
    log.info("Usuário cadastrado id=%s", usuario["id"])
    return {"mensagem": "Cadastro realizado com sucesso", "usuario": usuario}


@app.post("/login")
def login(dados: Login):
    usuario = executar(
        "SELECT id, email, senha_hash FROM usuarios WHERE email = %s",
        (dados.email.lower(),),
        "um",
    )
    if usuario is None or not verificar_senha(dados.senha, usuario["senha_hash"]):
        log.warning("Login falhou para o e-mail %s", dados.email)
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")
    log.info("Login realizado id=%s", usuario["id"])
    token = criar_token(usuario["id"], usuario["email"])
    return {"access_token": token, "token_type": "bearer"}


def buscar_usuario(usuario_id):
    usuario = executar(
        "SELECT id, nome, email, criado_em FROM usuarios WHERE id = %s",
        (usuario_id,),
        "um",
    )
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return usuario


@app.get("/usuarios/me")
def meus_dados(atual: dict = Depends(usuario_atual)):
    return buscar_usuario(atual["id"])


@app.get("/usuarios/{usuario_id}")
def consultar(usuario_id: int, atual: dict = Depends(usuario_atual)):
    if usuario_id != atual["id"]:
        raise HTTPException(status_code=403, detail="Você só pode ver seus dados")
    return buscar_usuario(usuario_id)


@app.put("/usuarios/{usuario_id}")
def atualizar(
    usuario_id: int, dados: UsuarioAtualizacao, atual: dict = Depends(usuario_atual)
):
    if usuario_id != atual["id"]:
        raise HTTPException(status_code=403, detail="Você só pode alterar seus dados")

    campos = []
    valores = []
    if dados.nome:
        campos.append("nome = %s")
        valores.append(dados.nome)
    if dados.email:
        campos.append("email = %s")
        valores.append(dados.email.lower())
    if dados.senha:
        campos.append("senha_hash = %s")
        valores.append(gerar_hash_senha(dados.senha))
    if not campos:
        raise HTTPException(status_code=400, detail="Nenhum dado para atualizar")

    valores.append(usuario_id)
    try:
        usuario = executar(
            f"UPDATE usuarios SET {', '.join(campos)} WHERE id = %s "
            "RETURNING id, nome, email",
            valores,
            "um",
        )
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(status_code=409, detail="E-mail já cadastrado")
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    log.info("Usuário atualizado id=%s", usuario_id)
    return usuario

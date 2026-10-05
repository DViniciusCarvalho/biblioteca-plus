import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

SEGREDO = os.getenv("JWT_SECRET", "segredo-somente-para-testes")
ALGORITMO = "HS256"
MINUTOS_DE_VALIDADE = 60

esquema = HTTPBearer(auto_error=False)


def gerar_hash_senha(senha):
    sal = secrets.token_hex(16)
    hash_ = hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(sal), 100_000)
    return f"{sal}${hash_.hex()}"


def verificar_senha(senha, senha_hash):
    sal, hash_salvo = senha_hash.split("$")
    novo = hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(sal), 100_000)
    return hmac.compare_digest(novo.hex(), hash_salvo)


def criar_token(usuario_id, email):
    validade = datetime.now(timezone.utc) + timedelta(minutes=MINUTOS_DE_VALIDADE)
    dados = {"sub": str(usuario_id), "email": email, "exp": validade}
    return jwt.encode(dados, SEGREDO, algorithm=ALGORITMO)


def usuario_atual(credenciais: HTTPAuthorizationCredentials = Depends(esquema)):
    if credenciais is None:
        raise HTTPException(status_code=401, detail="Token não informado")
    try:
        dados = jwt.decode(credenciais.credentials, SEGREDO, algorithms=[ALGORITMO])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")
    return {
        "id": int(dados["sub"]),
        "email": dados["email"],
        "token": credenciais.credentials,
    }

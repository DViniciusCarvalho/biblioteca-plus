import os

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

SEGREDO = os.getenv("JWT_SECRET", "segredo-somente-para-testes")
ALGORITMO = "HS256"

esquema = HTTPBearer(auto_error=False)


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

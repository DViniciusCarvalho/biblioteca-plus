import os
import psycopg2
from psycopg2.extras import RealDictCursor


def conectar():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "biblioteca"),
        user=os.getenv("POSTGRES_USER", "biblioteca_user"),
        password=os.getenv("POSTGRES_PASSWORD", "12345678"),
        connect_timeout=5,
        cursor_factory=RealDictCursor,
    )


def executar(sql, parametros=None, buscar="nenhum"):
    """Executa um comando SQL.

    buscar="um"     -> devolve uma linha (ou None)
    buscar="todos"  -> devolve uma lista de linhas
    buscar="nenhum" -> não devolve nada
    """
    conexao = conectar()
    try:
        with conexao.cursor() as cursor:
            cursor.execute(sql, parametros)
            if buscar == "um":
                resultado = cursor.fetchone()
            elif buscar == "todos":
                resultado = cursor.fetchall()
            else:
                resultado = None
        conexao.commit()
        return resultado
    finally:
        conexao.close()

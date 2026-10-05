"""Coleta métricas de qualidade de cada serviço e grava em metricas/relatorio_metricas.md.

Não precisa de Docker nem de banco. Execute na raiz do projeto:

    pip install -r requirements-dev.txt
    pip install -r servico_emprestimos/requirements.txt
    python testes/coletar_metricas.py

Métricas: testes que passaram/falharam, cobertura de código (%), linhas de código,
problemas do Ruff, formatação do Black e complexidade ciclomática média (Radon).
"""

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SERVICOS = [
    "servico_usuarios",
    "servico_livros",
    "servico_emprestimos",
    "servico_notificacoes",
]


def rodar(comando, pasta):
    resultado = subprocess.run(comando, cwd=pasta, capture_output=True, text=True)
    return resultado.returncode, resultado.stdout + resultado.stderr


def ferramenta_instalada(saida):
    return "No module named" not in saida


def testes_e_cobertura(pasta):
    codigo, saida = rodar(
        [sys.executable, "-m", "pytest", "--cov=app", "--cov-report=term", "-q"], pasta
    )
    if not ferramenta_instalada(saida):
        return "n/d", "n/d", "n/d"
    passaram = re.search(r"(\d+) passed", saida)
    falharam = re.search(r"(\d+) failed", saida)
    cobertura = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", saida)
    return (
        passaram.group(1) if passaram else "0",
        falharam.group(1) if falharam else "0",
        f"{cobertura.group(1)}%" if cobertura else "n/d",
    )


def linhas_de_codigo(pasta):
    total = 0
    for arquivo in (pasta / "app").glob("*.py"):
        for linha in arquivo.read_text(encoding="utf-8").splitlines():
            if linha.strip() and not linha.strip().startswith("#"):
                total += 1
    return total


def problemas_ruff(pasta):
    codigo, saida = rodar(
        [sys.executable, "-m", "ruff", "check", ".", "--output-format", "concise"],
        pasta,
    )
    if not ferramenta_instalada(saida):
        return "n/d"
    return str(len(re.findall(r"\.py:\d+:\d+:", saida)))


def formatacao_black(pasta):
    codigo, saida = rodar([sys.executable, "-m", "black", "--check", "."], pasta)
    if not ferramenta_instalada(saida):
        return "n/d"
    return "OK" if codigo == 0 else "precisa de 'black .'"


def complexidade(pasta):
    codigo, saida = rodar(
        [sys.executable, "-m", "radon", "cc", "-s", "-a", "app"], pasta
    )
    if not ferramenta_instalada(saida):
        return "n/d"
    achou = re.search(r"Average complexity: (\w) \(([\d.]+)\)", saida)
    return f"{achou.group(2)} ({achou.group(1)})" if achou else "n/d"


def main():
    linhas = [
        "| Serviço | Testes OK | Testes com falha | Cobertura | Linhas de código | Ruff | Black | Complexidade média |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for nome in SERVICOS:
        pasta = RAIZ / nome
        ok, falha, cobertura = testes_e_cobertura(pasta)
        linha = (
            f"| {nome} | {ok} | {falha} | {cobertura} | {linhas_de_codigo(pasta)} | "
            f"{problemas_ruff(pasta)} | {formatacao_black(pasta)} | {complexidade(pasta)} |"
        )
        linhas.append(linha)
        print(linha)

    Path(RAIZ / "metricas").mkdir(exist_ok=True)
    destino = RAIZ / "metricas" / "relatorio_metricas.md"
    cabecalho = (
        f"# Métricas de qualidade\n\nGerado em {datetime.now():%d/%m/%Y %H:%M}\n\n"
    )
    legenda = (
        "\n\n- **Cobertura**: % das linhas do código executadas pelos testes (pytest-cov)."
        "\n- **Ruff**: quantidade de problemas apontados pela análise estática (0 é o ideal)."
        "\n- **Complexidade média**: complexidade ciclomática (Radon). A = simples, B = moderada."
        "\n"
    )
    destino.write_text(cabecalho + "\n".join(linhas) + legenda, encoding="utf-8")
    print(f"\nRelatório salvo em {destino}")


if __name__ == "__main__":
    main()

"""Teste de carga com Locust.

  pip install locust
  locust -f testes/locustfile.py --host http://localhost:8080

Depois abra http://localhost:8089, informe o número de usuários simultâneos e inicie.
"""

from locust import HttpUser, between, task


class Leitor(HttpUser):
    wait_time = between(0.5, 1.5)

    @task(3)
    def listar_livros(self):
        self.client.get("/livros")

    @task(1)
    def buscar_por_titulo(self):
        self.client.get("/livros?titulo=dom")

    @task(1)
    def ver_saude(self):
        self.client.get("/saude")

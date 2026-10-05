const viaGateway = ["", "80", "8080", "443"].includes(location.port);
window.API = viaGateway
  ? { usuarios: "", livros: "", emprestimos: "", notificacoes: "" }
  : {
      usuarios: "http://localhost:8001",
      livros: "http://localhost:8002",
      emprestimos: "http://localhost:8003",
      notificacoes: "http://localhost:8004",
    };

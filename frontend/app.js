
const $ = (s) => document.querySelector(s);
const esc = (t) => String(t ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const data = (d) => (d ? new Date(d).toLocaleDateString("pt-BR") : "-");
const lombada = (t) => `hsl(${[...t].reduce((a, c) => a + c.charCodeAt(0) * 7, 0) % 360} 38% 38%)`;

let token = localStorage.getItem("token");

function aviso(msg, erro = false) {
  const el = $("#aviso");
  el.textContent = msg;
  el.className = erro ? "mostrar erro" : "mostrar";
  clearTimeout(aviso.t);
  aviso.t = setTimeout(() => (el.className = ""), 3500);
}


async function api(servico, caminho, { metodo = "GET", corpo, auth = true } = {}) {
  const cab = { "Content-Type": "application/json" };
  if (auth && token) cab.Authorization = "Bearer " + token;
  let r;
  try {
    r = await fetch(API[servico] + caminho, { method: metodo, headers: cab, body: corpo && JSON.stringify(corpo) });
  } catch {
    throw new Error("Não foi possível conectar ao servidor.");
  }
  const dados = await r.json().catch(() => null);
  if (r.status === 401 && auth) { sair(); throw new Error("Sessão expirada. Entre novamente."); }
  if (!r.ok) throw new Error(typeof dados?.detail === "string" ? dados.detail : "Dados inválidos. Confira os campos.");
  return dados;
}

const seguro = async (fn) => { try { await fn(); } catch (e) { aviso(e.message, true); } };


async function entrar(email, senha) {
  const r = await api("usuarios", "/login", { metodo: "POST", corpo: { email, senha }, auth: false });
  token = r.access_token;
  localStorage.setItem("token", token);
  iniciar();
}
const campos = (form) => Object.fromEntries(new FormData(form));

$("#form-entrar").onsubmit = (e) => { e.preventDefault(); const f = campos(e.target); seguro(() => entrar(f.email, f.senha)); };
$("#form-cadastrar").onsubmit = (e) => {
  e.preventDefault();
  const f = campos(e.target);
  seguro(async () => {
    await api("usuarios", "/usuarios", { metodo: "POST", corpo: f, auth: false });
    aviso("Conta criada! Entrando...");
    await entrar(f.email, f.senha);
  });
};
document.querySelectorAll("[data-form]").forEach((b) => (b.onclick = () => {
  document.querySelectorAll("[data-form]").forEach((x) => x.classList.toggle("ativa", x === b));
  $("#form-entrar").hidden = b.dataset.form !== "entrar";
  $("#form-cadastrar").hidden = b.dataset.form !== "cadastrar";
}));

function sair() {
  localStorage.removeItem("token");
  token = null;
  iniciar();
}
$("#sair").onclick = sair;


async function carregarLivros() {
  const p = new URLSearchParams();
  if ($("#busca").value.trim()) p.set("titulo", $("#busca").value.trim());
  if ($("#so-disp").checked) p.set("somente_disponiveis", "true");
  const livros = await api("livros", "/livros?" + p, { auth: false });
  $("#lista-livros").innerHTML = livros.length
    ? livros.map((l) => `
      <article class="item" style="--lombada:${lombada(l.titulo)}">
        <div><h3>${esc(l.titulo)}</h3><p>${esc(l.autor)}${l.ano ? ", " + l.ano : ""}</p></div>
        <div class="acoes">
          <span class="selo ${l.disponivel ? "ok" : "no"}">${l.disponivel ? "Disponível" : "Emprestado"}</span>
          <button data-emprestar="${l.id}" ${l.disponivel ? "" : "disabled"}>Emprestar</button>
        </div>
      </article>`).join("")
    : '<p class="vazio">Nenhum livro encontrado.</p>';
}
let temporizador;
$("#busca").oninput = () => { clearTimeout(temporizador); temporizador = setTimeout(() => seguro(carregarLivros), 300); };
$("#so-disp").onchange = () => seguro(carregarLivros);
$("#lista-livros").onclick = (e) => {
  const id = e.target.dataset.emprestar;
  if (!id) return;
  seguro(async () => {
    await api("emprestimos", "/emprestimos", { metodo: "POST", corpo: { livro_id: Number(id) } });
    aviso("Empréstimo realizado! Prazo de 14 dias.");
    await carregarLivros();
  });
};
$("#form-livro").onsubmit = (e) => {
  e.preventDefault();
  const f = campos(e.target);
  f.ano = f.ano ? Number(f.ano) : null;
  seguro(async () => {
    await api("livros", "/livros", { metodo: "POST", corpo: f });
    e.target.reset();
    e.target.closest("details").open = false;
    aviso("Livro cadastrado.");
    await carregarLivros();
  });
};

async function carregarEmprestimos() {
  const [lista, livros] = await Promise.all([
    api("emprestimos", "/emprestimos"),
    api("livros", "/livros", { auth: false }),
  ]);
  const titulos = Object.fromEntries(livros.map((l) => [l.id, l.titulo]));
  $("#lista-emprestimos").innerHTML = lista.length
    ? lista.map((e) => {
        const titulo = titulos[e.livro_id] || "Livro " + e.livro_id;
        const ativo = e.status === "ativo";
        const detalhe = ativo ? `Retirado em ${data(e.data_emprestimo)}, devolver até ${data(e.data_prevista_devolucao)}`
          : `Retirado em ${data(e.data_emprestimo)}, encerrado em ${data(e.data_devolucao)}`;
        return `<article class="item" style="--lombada:${lombada(titulo)}">
          <div><h3>${esc(titulo)}</h3><p>${detalhe}</p></div>
          <div class="acoes">
            <span class="selo ${ativo ? "no" : "ok"}">${esc(e.status)}</span>
            ${ativo ? `<button data-devolver="${e.id}">Devolver</button><button class="perigo" data-cancelar="${e.id}">Cancelar</button>` : ""}
          </div></article>`;
      }).join("")
    : '<p class="vazio">Você ainda não fez nenhum empréstimo.</p>';
}
$("#lista-emprestimos").onclick = (e) => {
  const { devolver, cancelar } = e.target.dataset;
  const id = devolver || cancelar;
  if (!id) return;
  seguro(async () => {
    await api("emprestimos", `/emprestimos/${id}/${devolver ? "devolucao" : "cancelar"}`, { metodo: "POST" });
    aviso(devolver ? "Devolução registrada." : "Empréstimo cancelado.");
    await carregarEmprestimos();
  });
};

async function carregarNotificacoes() {
  const lista = await api("notificacoes", "/notificacoes");
  $("#lista-notificacoes").innerHTML = lista.length
    ? lista.map((n) => `<article class="item"><div><h3>${esc(n.mensagem)}</h3><p>${data(n.criado_em)}</p></div></article>`).join("")
    : '<p class="vazio">Nenhum aviso por enquanto.</p>';
}

const carregadores = { livros: carregarLivros, emprestimos: carregarEmprestimos, notificacoes: carregarNotificacoes };
function abrirAba(nome) {
  document.querySelectorAll("[data-aba]").forEach((b) => b.classList.toggle("ativa", b.dataset.aba === nome));
  document.querySelectorAll(".painel").forEach((p) => (p.hidden = p.id !== "painel-" + nome));
  seguro(carregadores[nome]);
}
document.querySelectorAll("[data-aba]").forEach((b) => (b.onclick = () => abrirAba(b.dataset.aba)));

async function iniciar() {
  $("#tela-auth").hidden = !!token;
  $("#tela-app").hidden = !token;
  $("#usuario").hidden = !token;
  if (!token) return;
  await seguro(async () => { $("#nome").textContent = (await api("usuarios", "/usuarios/me")).nome; });
  if (token) abrirAba("livros");
}
iniciar();

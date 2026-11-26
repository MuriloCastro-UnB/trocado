import os
from datetime import date

from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, url_for

import armazenamento
import financas
import interpretador

# lê o arquivo .env (se existir) e coloca as configurações nas variáveis de ambiente
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

app = Flask(__name__)

# arquivo onde os dados ficam; os testes trocam por um arquivo temporário
app.config["ARQUIVO_DADOS"] = armazenamento.ARQUIVO_DADOS

# chave e modelo do Gemini; sem chave, o app usa só as regras
app.config["GEMINI_CHAVE"] = os.getenv("GEMINI_API_KEY", "").strip()
app.config["GEMINI_MODELO"] = os.getenv("GEMINI_MODELO", "").strip()
if app.config["GEMINI_MODELO"] == "":
    app.config["GEMINI_MODELO"] = interpretador.MODELO_PADRAO

# funções que as páginas HTML podem usar, como {{ valor | reais }}
app.jinja_env.filters["reais"] = financas.formatar_reais
app.jinja_env.filters["data"] = financas.formatar_data
app.jinja_env.filters["categoria"] = financas.nome_categoria
app.jinja_env.filters["nome_mes"] = financas.nome_mes


def carregar():
    return armazenamento.carregar_dados(app.config["ARQUIVO_DADOS"])


def salvar(dados):
    armazenamento.salvar_dados(dados, app.config["ARQUIVO_DADOS"])


# Depois de salvar algo, as rotas usam redirect para outra página com a mensagem
# no endereço. Assim, se a pessoa apertar F5, o formulário não é enviado de novo.


def ler_valor(texto):
    # lê um valor digitado no formulário, como "500", "500,00" ou "R$ 1.200,50"
    # devolve o valor em centavos e uma mensagem de erro (vazia se deu certo)
    texto = texto.strip().lower().replace(" ", "")
    if texto == "":
        return None, "Digite um valor."
    if texto.startswith("-"):
        return None, "O valor não pode ser negativo."
    valor = interpretador.converter_valor(texto)
    if valor is None:
        return None, "Valor inválido. Use só números, como 500 ou 500,00."
    return valor, ""


def ler_data(texto):
    # devolve a data, ou None se o texto não for uma data válida
    try:
        return date.fromisoformat(texto.strip())
    except ValueError:
        return None


def mes_valido(texto):
    # aceita "AAAA-MM", como "2026-11"
    if len(texto) != 7 or texto[4] != "-":
        return False
    if not texto[0:4].isdigit() or not texto[5:7].isdigit():
        return False
    numero = int(texto[5:7])
    return numero >= 1 and numero <= 12


def mostrar_chat(frase="", resposta="", confirmacao=None, erro=""):
    dados = carregar()
    # os 5 últimos registros, do mais novo para o mais antigo
    ultimas = dados["transacoes"][-5:]
    ultimas.reverse()
    return render_template("chat.html", frase=frase, resposta=resposta, confirmacao=confirmacao,
                           erro=erro, ultimas=ultimas, categorias=financas.CATEGORIAS_GASTO)


@app.route("/", methods=["GET", "POST"])
def chat():
    if request.method == "GET":
        return mostrar_chat()

    frase = request.form.get("mensagem", "").strip()
    if frase == "":
        return mostrar_chat(erro="Escreva uma mensagem.")

    hoje = date.today()
    resposta = interpretador.responder_pergunta(frase, carregar(), hoje)
    if resposta is not None:
        return mostrar_chat(frase=frase, resposta=resposta)

    interpretacao = interpretador.interpretar(frase, hoje, app.config["GEMINI_CHAVE"], app.config["GEMINI_MODELO"])
    if "erro" in interpretacao:
        return mostrar_chat(frase=frase, erro=interpretacao["erro"])

    # ainda não salva: mostra o que entendeu e espera a confirmação
    interpretacao["texto"] = interpretador.texto_confirmacao(interpretacao, hoje)
    return mostrar_chat(frase=frase, confirmacao=interpretacao)


def erro_na_transacao(tipo, valor, categoria, data):
    # os dados vêm de campos escondidos, mas mesmo assim é bom conferir
    if tipo != "gasto" and tipo != "entrada":
        return "Tipo inválido."
    if not valor.isdigit() or int(valor) <= 0:
        return "Valor inválido."
    if tipo == "gasto" and categoria not in financas.CATEGORIAS_GASTO:
        return "Escolha uma categoria válida."
    if ler_data(data) is None:
        return "Data inválida."
    return ""


@app.route("/confirmar", methods=["POST"])
def confirmar():
    if request.form.get("acao") != "confirmar":
        return redirect(url_for("chat", mensagem="Registro cancelado. Nada foi salvo."))

    tipo = request.form.get("tipo", "")
    valor = request.form.get("valor", "")
    categoria = request.form.get("categoria", "")
    data = request.form.get("data", "")
    descricao = request.form.get("descricao", "").strip()

    erro = erro_na_transacao(tipo, valor, categoria, data)
    if erro != "":
        return mostrar_chat(erro=erro)

    if tipo == "entrada":
        categoria = "entrada"
    data = ler_data(data).isoformat()

    dados = carregar()
    financas.adicionar_transacao(dados, tipo, int(valor), categoria, descricao, data)
    salvar(dados)

    texto_valor = financas.formatar_reais(int(valor))
    if tipo == "entrada":
        mensagem = "Registro salvo: entrada de " + texto_valor + " em " + financas.formatar_data(data) + "."
    else:
        mensagem = ("Registro salvo: gasto de " + texto_valor + " em " + financas.nome_categoria(categoria)
                    + ", " + financas.formatar_data(data) + ".")

    # confere o limite da categoria no mês do gasto
    aviso = ""
    if tipo == "gasto":
        situacao = financas.verificar_limite(dados, categoria, data[0:7])
        if situacao is not None:
            aviso = situacao["aviso"]

    return redirect(url_for("chat", mensagem=mensagem, aviso=aviso))


def mostrar_transacoes(erro=""):
    dados = carregar()
    mes = financas.mes_de(date.today())
    lista = financas.transacoes_do_mes(dados, mes)
    return render_template("transacoes.html", transacoes=lista, mes=mes, erro=erro)


@app.route("/transacoes")
def transacoes():
    return mostrar_transacoes()


@app.route("/excluir", methods=["POST"])
def excluir():
    id_texto = request.form.get("id", "")
    if not id_texto.isdigit():
        return mostrar_transacoes(erro="Registro inválido.")

    dados = carregar()
    if not financas.excluir_transacao(dados, int(id_texto)):
        return mostrar_transacoes(erro="Esse registro não existe mais.")
    salvar(dados)
    return redirect(url_for("transacoes", mensagem="Registro excluído."))


def mostrar_limites(erro=""):
    dados = carregar()
    mes = financas.mes_de(date.today())
    return render_template("limites.html", limites=financas.situacao_limites(dados, mes), mes=mes,
                           categorias=financas.CATEGORIAS_GASTO, erro=erro)


@app.route("/limites")
def limites():
    return mostrar_limites()


@app.route("/limites/definir", methods=["POST"])
def salvar_limite():
    categoria = request.form.get("categoria", "")
    if categoria not in financas.CATEGORIAS_GASTO:
        return mostrar_limites(erro="Escolha uma categoria válida.")

    valor, erro = ler_valor(request.form.get("valor", ""))
    if erro != "":
        return mostrar_limites(erro=erro)

    dados = carregar()
    financas.definir_limite(dados, categoria, valor)
    salvar(dados)

    nome = financas.nome_categoria(categoria)
    if valor == 0:
        mensagem = "Limite de " + nome + " removido."
    else:
        mensagem = "Limite de " + nome + " definido em " + financas.formatar_reais(valor) + " por mês."
    return redirect(url_for("limites", mensagem=mensagem))


def mostrar_metas(erro=""):
    dados = carregar()
    metas = financas.progresso_metas(dados, date.today())
    return render_template("metas.html", metas=metas, erro=erro)


@app.route("/metas")
def metas():
    return mostrar_metas()


@app.route("/metas/criar", methods=["POST"])
def nova_meta():
    nome = request.form.get("nome", "").strip()
    if nome == "":
        return mostrar_metas(erro="Digite o nome da meta.")

    alvo, erro = ler_valor(request.form.get("valor", ""))
    if erro != "":
        return mostrar_metas(erro=erro)
    if alvo == 0:
        return mostrar_metas(erro="O valor da meta precisa ser maior que zero.")

    prazo = ler_data(request.form.get("prazo", ""))
    if prazo is None:
        return mostrar_metas(erro="Escolha um prazo válido.")
    if prazo <= date.today():
        return mostrar_metas(erro="O prazo precisa ser depois de hoje.")

    dados = carregar()
    financas.criar_meta(dados, nome, alvo, prazo.isoformat())
    salvar(dados)
    return redirect(url_for("metas", mensagem="Meta " + nome + " criada."))


@app.route("/metas/guardar", methods=["POST"])
def guardar_dinheiro():
    id_texto = request.form.get("id", "")
    if not id_texto.isdigit():
        return mostrar_metas(erro="Meta inválida.")

    valor, erro = ler_valor(request.form.get("valor", ""))
    if erro != "":
        return mostrar_metas(erro=erro)
    if valor == 0:
        return mostrar_metas(erro="O valor guardado precisa ser maior que zero.")

    dados = carregar()
    meta = financas.guardar_na_meta(dados, int(id_texto), valor)
    if meta is None:
        return mostrar_metas(erro="Essa meta não existe.")
    salvar(dados)

    mensagem = financas.formatar_reais(valor) + " guardados na meta " + meta["nome"] + "."
    if meta["guardado"] >= meta["alvo"]:
        mensagem = mensagem + " Parabéns, você completou a meta!"
    return redirect(url_for("metas", mensagem=mensagem))


@app.route("/resumo")
def resumo():
    dados = carregar()
    mes_atual = financas.mes_de(date.today())
    mes = request.args.get("mes", mes_atual)

    erro = ""
    if not mes_valido(mes):
        erro = "Mês inválido. Mostrando o mês atual."
        mes = mes_atual

    meses = financas.meses_com_registros(dados, mes_atual)
    if mes not in meses:
        meses.append(mes)
        meses.sort(reverse=True)

    return render_template("resumo.html", resumo=financas.resumo_do_mes(dados, mes), mes=mes, meses=meses,
                           categorias=financas.CATEGORIAS_GASTO, erro=erro)


if __name__ == "__main__":
    # avisa no terminal qual interpretador está ligado, sem nunca mostrar a chave
    if app.config["GEMINI_CHAVE"] != "":
        print("Gemini ligado, modelo " + app.config["GEMINI_MODELO"] + ". Se ele falhar, uso as regras.")
    else:
        print("Sem chave do Gemini no .env: as frases serão entendidas pelas regras.")
    app.run(debug=False)

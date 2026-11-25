from datetime import timedelta

import financas

ACENTOS = {"á": "a", "à": "a", "â": "a", "ã": "a", "é": "e", "ê": "e", "í": "i",
           "ó": "o", "ô": "o", "õ": "o", "ú": "u", "ü": "u", "ç": "c"}

PALAVRAS_GASTO = ["gastei", "paguei", "comprei"]
PALAVRAS_ENTRADA = ["recebi", "ganhei", "salario", "bolsa", "mesada", "vendi"]

# palavras sem acento, porque a frase também perde os acentos antes da busca
PALAVRAS_CATEGORIA = {
    "alimentacao": ["alimentacao", "comida", "ifood", "mercado", "supermercado", "restaurante",
                    "lanche", "lanchonete", "almoco", "jantar", "cafe", "pizza", "padaria",
                    "hamburguer", "acai", "ru", "bandejao", "feira", "sorvete"],
    "transporte": ["transporte", "uber", "onibus", "metro", "gasolina", "combustivel", "taxi",
                   "passagem", "estacionamento"],
    "moradia": ["moradia", "aluguel", "luz", "energia", "agua", "condominio", "internet", "gas"],
    "lazer": ["lazer", "cinema", "show", "netflix", "spotify", "jogo", "bar", "festa", "ingresso"],
    "saude": ["saude", "farmacia", "remedio", "medico", "consulta", "dentista", "exame",
              "hospital", "academia"],
    "educacao": ["educacao", "livro", "curso", "faculdade", "xerox", "apostila", "material",
                 "mensalidade"],
    "compras": ["compras", "roupa", "tenis", "camisa", "calca", "sapato", "celular", "presente",
                "shopping", "bolsa", "fone"],
    "outros": ["outros"],
}

PALAVRAS_PERGUNTA = ["quanto", "qual", "quais", "como"]

# palavras que costumam vir logo antes do valor: "por 90", "de 45", "custou 30"
PALAVRAS_ANTES_DO_VALOR = ["r$", "por", "de", "custou", "deu", "foi"]


def tirar_acentos(texto):
    novo = ""
    for letra in texto:
        if letra in ACENTOS:
            novo = novo + ACENTOS[letra]
        else:
            novo = novo + letra
    return novo


def separar_palavras(frase):
    # minúsculas, sem acento e sem pontuação nas pontas de cada palavra
    texto = tirar_acentos(frase.lower())
    palavras = []
    for palavra in texto.split():
        palavra = palavra.strip(".,!?;:()\"'")
        if palavra != "":
            palavras.append(palavra)
    return palavras


def tem_alguma(palavras, lista):
    for palavra in palavras:
        if palavra in lista:
            return True
    return False


def converter_valor(palavra):
    # transforma "35", "35,90", "35.90", "r$35" ou "1.200,50" em centavos
    # devolve None se a palavra não for um valor
    if palavra.startswith("r$"):
        palavra = palavra[2:]

    if "," in palavra:
        # a vírgula separa os centavos e os pontos separam os milhares
        partes = palavra.split(",")
        if len(partes) != 2:
            return None
        reais = partes[0].replace(".", "")
        centavos = partes[1]
    else:
        partes = palavra.split(".")
        if len(partes) == 2 and len(partes[1]) <= 2:
            # 35.90: o ponto separa os centavos
            reais = partes[0]
            centavos = partes[1]
        else:
            # 35 ou 1.200: não tem centavos
            reais = palavra.replace(".", "")
            centavos = "00"

    if not reais.isdigit() or not centavos.isdigit() or len(centavos) > 2:
        return None
    if len(centavos) == 1:
        centavos = centavos + "0"
    return int(reais) * 100 + int(centavos)


def encontrar_valor(palavras):
    # prefere o número que vem logo depois de "r$", "por", "de"...
    # assim "comprei 2 camisas por 90" dá 90, e não 2
    for i in range(len(palavras)):
        valor = converter_valor(palavras[i])
        if valor is not None:
            if palavras[i].startswith("r$"):
                return valor
            if i > 0 and palavras[i - 1] in PALAVRAS_ANTES_DO_VALOR:
                return valor

    # se nenhum número veio depois dessas palavras, usa o primeiro
    for palavra in palavras:
        valor = converter_valor(palavra)
        if valor is not None:
            return valor
    return None


def encontrar_tipo(palavras):
    # "gastei", "paguei" e "comprei" vêm primeiro: "comprei uma bolsa" é gasto
    if tem_alguma(palavras, PALAVRAS_GASTO):
        return "gasto"
    if tem_alguma(palavras, PALAVRAS_ENTRADA):
        return "entrada"
    return "gasto"


def encontrar_categoria(palavras):
    # devolve None se nenhuma palavra da frase estiver no dicionário
    for categoria in PALAVRAS_CATEGORIA:
        lista = PALAVRAS_CATEGORIA[categoria]
        for palavra in palavras:
            if palavra in lista:
                return categoria
            # aceita o plural: "remedios" vira "remedio"
            if palavra.endswith("s") and palavra[:-1] in lista:
                return categoria
    return None


def encontrar_data(palavras, hoje):
    if "anteontem" in palavras:
        return hoje - timedelta(days=2)
    if "ontem" in palavras:
        return hoje - timedelta(days=1)
    return hoje


def interpretar_frase(frase, hoje):
    palavras = separar_palavras(frase)
    if len(palavras) == 0:
        return {"erro": "Escreva uma frase, por exemplo: gastei 35 no ifood."}

    valor = encontrar_valor(palavras)
    if valor is None:
        return {"erro": "Não encontrei o valor na frase. Tente algo como: gastei 35 no ifood."}
    if valor == 0:
        return {"erro": "O valor precisa ser maior que zero."}

    tipo = encontrar_tipo(palavras)
    if tipo == "entrada":
        categoria = "entrada"
    else:
        categoria = encontrar_categoria(palavras)
        if categoria is None:
            categoria = "outros"

    data = encontrar_data(palavras, hoje)
    return {
        "tipo": tipo,
        "valor": valor,
        "categoria": categoria,
        "data": data.isoformat(),
        "descricao": frase.strip(),
    }


def texto_confirmacao(interpretacao, hoje):
    # monta "Entendi: gasto de R$ 35,00 em Alimentação, hoje. Confirmar?"
    data = interpretacao["data"]
    if data == hoje.isoformat():
        quando = "hoje"
    elif data == (hoje - timedelta(days=1)).isoformat():
        quando = "ontem"
    elif data == (hoje - timedelta(days=2)).isoformat():
        quando = "anteontem"
    else:
        quando = "em " + financas.formatar_data(data)

    valor = financas.formatar_reais(interpretacao["valor"])
    if interpretacao["tipo"] == "entrada":
        return "Entendi: entrada de " + valor + ", " + quando + ". Confirmar?"
    nome = financas.nome_categoria(interpretacao["categoria"])
    return "Entendi: gasto de " + valor + " em " + nome + ", " + quando + ". Confirmar?"


def e_pergunta(frase, palavras):
    if "?" in frase:
        return True
    # "quanto gastei com uber" começa com palavra de pergunta
    if len(palavras) > 0 and palavras[0] in PALAVRAS_PERGUNTA:
        return True
    # "me diz quanto gastei" não tem valor, então não pode ser um gasto
    # já "comprei um presente como lembrança por 50" tem valor e não é pergunta
    if encontrar_valor(palavras) is None and tem_alguma(palavras, PALAVRAS_PERGUNTA):
        return True
    return False


def resposta_saldo(dados, mes):
    totais = financas.totais_do_mes(dados, mes)
    return ("Em " + financas.nome_mes(mes) + " você recebeu " + financas.formatar_reais(totais["entradas"])
            + " e gastou " + financas.formatar_reais(totais["gastos"]) + ". Seu saldo do mês é "
            + financas.formatar_reais(totais["saldo"]) + ".")


def resposta_gasto(dados, mes, categoria):
    if categoria is None:
        total = financas.totais_do_mes(dados, mes)["gastos"]
        return "Em " + financas.nome_mes(mes) + " você gastou " + financas.formatar_reais(total) + " no total."

    gastos = financas.gastos_por_categoria(dados, mes)
    gasto = 0
    if categoria in gastos:
        gasto = gastos[categoria]
    texto = ("Em " + financas.nome_mes(mes) + " você gastou " + financas.formatar_reais(gasto)
             + " com " + financas.nome_categoria(categoria) + ".")

    limite = financas.verificar_limite(dados, categoria, mes)
    if limite is not None:
        texto = (texto + " Seu limite é " + financas.formatar_reais(limite["limite"])
                 + " e você já usou " + str(limite["porcentagem"]) + "%.")
    return texto


def resposta_metas(dados, hoje):
    metas = financas.progresso_metas(dados, hoje)
    if len(metas) == 0:
        return "Você ainda não tem metas."

    linhas = []
    for meta in metas:
        guardado = financas.formatar_reais(meta["guardado"]) + " de " + financas.formatar_reais(meta["alvo"])
        if meta["concluida"]:
            linhas.append(meta["nome"] + ": meta concluída (" + guardado + ").")
        else:
            linhas.append(meta["nome"] + ": " + guardado + " (" + str(meta["porcentagem"]) + "%). Faltam "
                          + financas.formatar_reais(meta["falta"]) + ", então guarde "
                          + financas.formatar_reais(meta["por_mes"]) + " por mês até "
                          + financas.formatar_data(meta["prazo"]) + ".")
    return "\n".join(linhas)


def responder_pergunta(frase, dados, hoje):
    # devolve None quando a frase não é uma pergunta (aí ela deve ser um gasto ou entrada)
    palavras = separar_palavras(frase)
    if not e_pergunta(frase, palavras):
        return None

    mes = financas.mes_de(hoje)
    if "saldo" in palavras:
        return resposta_saldo(dados, mes)
    if "meta" in palavras or "metas" in palavras:
        return resposta_metas(dados, hoje)
    if tem_alguma(palavras, ["gastei", "gasto", "gastos"]):
        return resposta_gasto(dados, mes, encontrar_categoria(palavras))

    return ("Não entendi a pergunta. Você pode perguntar, por exemplo: \"qual meu saldo?\", "
            "\"quanto gastei com transporte esse mês?\" ou \"como estão minhas metas?\"")

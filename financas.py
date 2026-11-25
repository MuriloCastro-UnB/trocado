from datetime import date

# As funções que mudam os dados (adicionar, excluir, criar meta...) só mexem
# no dicionário. Quem chama precisa salvar depois com armazenamento.salvar_dados.

CATEGORIAS_GASTO = ["alimentacao", "transporte", "moradia", "lazer", "saude", "educacao", "compras", "outros"]

NOMES_CATEGORIAS = {
    "alimentacao": "Alimentação",
    "transporte": "Transporte",
    "moradia": "Moradia",
    "lazer": "Lazer",
    "saude": "Saúde",
    "educacao": "Educação",
    "compras": "Compras",
    "outros": "Outros",
    "entrada": "Entrada",
}

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]


def formatar_reais(centavos):
    sinal = ""
    if centavos < 0:
        sinal = "-"
        centavos = -centavos
    reais = str(centavos // 100)
    resto = str(centavos % 100)
    if len(resto) == 1:
        resto = "0" + resto

    # coloca o ponto a cada 3 dígitos, de trás para frente: 1234567 -> 1.234.567
    grupos = []
    while len(reais) > 3:
        grupos.insert(0, reais[-3:])
        reais = reais[:-3]
    grupos.insert(0, reais)

    return sinal + "R$ " + ".".join(grupos) + "," + resto


def formatar_data(data):
    # "2026-11-25" -> "25/11/2026"
    partes = data.split("-")
    return partes[2] + "/" + partes[1] + "/" + partes[0]


def nome_categoria(categoria):
    if categoria in NOMES_CATEGORIAS:
        return NOMES_CATEGORIAS[categoria]
    return categoria


def mes_de(dia):
    # date(2026, 11, 25) -> "2026-11"
    return dia.strftime("%Y-%m")


def nome_mes(mes):
    # "2026-11" -> "novembro de 2026"
    numero = int(mes[5:7])
    return MESES[numero - 1] + " de " + mes[0:4]


def totais_do_mes(dados, mes):
    entradas = 0
    gastos = 0
    for transacao in dados["transacoes"]:
        if transacao["data"].startswith(mes):
            if transacao["tipo"] == "entrada":
                entradas = entradas + transacao["valor"]
            else:
                gastos = gastos + transacao["valor"]
    return {"entradas": entradas, "gastos": gastos, "saldo": entradas - gastos}


def gastos_por_categoria(dados, mes):
    totais = {}
    for transacao in dados["transacoes"]:
        if transacao["tipo"] == "gasto" and transacao["data"].startswith(mes):
            categoria = transacao["categoria"]
            if categoria not in totais:
                totais[categoria] = 0
            totais[categoria] = totais[categoria] + transacao["valor"]
    return totais


def verificar_limite(dados, categoria, mes):
    # devolve None se a categoria não tem limite
    if categoria not in dados["limites"]:
        return None

    limite = dados["limites"][categoria]
    gastos = gastos_por_categoria(dados, mes)
    gasto = 0
    if categoria in gastos:
        gasto = gastos[categoria]

    porcentagem = 0
    if limite > 0:
        porcentagem = gasto * 100 // limite

    nome = nome_categoria(categoria)
    if gasto > limite:
        situacao = "estourou"
        aviso = ("Atenção: você passou do limite de " + nome + ". Gastou " + formatar_reais(gasto)
                 + " de " + formatar_reais(limite) + " (" + str(porcentagem) + "%).")
    elif porcentagem >= 80:
        situacao = "alerta"
        aviso = ("Cuidado: você já usou " + str(porcentagem) + "% do limite de " + nome
                 + " (" + formatar_reais(gasto) + " de " + formatar_reais(limite) + ").")
    else:
        situacao = "ok"
        aviso = ""

    return {
        "categoria": categoria,
        "nome": nome,
        "gasto": gasto,
        "limite": limite,
        "porcentagem": porcentagem,
        "situacao": situacao,
        "aviso": aviso,
    }


def situacao_limites(dados, mes):
    lista = []
    for categoria in CATEGORIAS_GASTO:
        situacao = verificar_limite(dados, categoria, mes)
        if situacao is not None:
            lista.append(situacao)
    return lista


def definir_limite(dados, categoria, valor):
    # limite 0 (ou menos) tira o limite da categoria
    if valor <= 0:
        if categoria in dados["limites"]:
            del dados["limites"][categoria]
    else:
        dados["limites"][categoria] = valor


def meses_ate(prazo, hoje):
    # conta quantas viradas de mês faltam até o prazo (no mínimo 1)
    data_prazo = date.fromisoformat(prazo)
    meses = (data_prazo.year - hoje.year) * 12 + (data_prazo.month - hoje.month)
    if meses < 1:
        meses = 1
    return meses


def progresso_meta(meta, hoje):
    falta = meta["alvo"] - meta["guardado"]
    if falta < 0:
        falta = 0

    porcentagem = 0
    if meta["alvo"] > 0:
        porcentagem = meta["guardado"] * 100 // meta["alvo"]

    # divide o que falta pelos meses e arredonda para cima
    meses = meses_ate(meta["prazo"], hoje)
    por_mes = falta // meses
    if falta % meses != 0:
        por_mes = por_mes + 1

    return {
        "id": meta["id"],
        "nome": meta["nome"],
        "alvo": meta["alvo"],
        "guardado": meta["guardado"],
        "prazo": meta["prazo"],
        "porcentagem": porcentagem,
        "falta": falta,
        "meses_restantes": meses,
        "por_mes": por_mes,
        "concluida": falta == 0,
    }


def progresso_metas(dados, hoje):
    lista = []
    for meta in dados["metas"]:
        lista.append(progresso_meta(meta, hoje))
    return lista


def criar_meta(dados, nome, alvo, prazo):
    meta = {
        "id": proximo_id(dados["metas"]),
        "nome": nome,
        "alvo": alvo,
        "guardado": 0,
        "prazo": prazo,
    }
    dados["metas"].append(meta)
    return meta


def guardar_na_meta(dados, id_meta, valor):
    # devolve a meta atualizada, ou None se a meta não existe
    for meta in dados["metas"]:
        if meta["id"] == id_meta:
            meta["guardado"] = meta["guardado"] + valor
            return meta
    return None


def proximo_id(lista):
    maior = 0
    for item in lista:
        if item["id"] > maior:
            maior = item["id"]
    return maior + 1


def adicionar_transacao(dados, tipo, valor, categoria, descricao, data):
    transacao = {
        "id": proximo_id(dados["transacoes"]),
        "tipo": tipo,
        "valor": valor,
        "categoria": categoria,
        "descricao": descricao,
        "data": data,
    }
    dados["transacoes"].append(transacao)
    return transacao


def excluir_transacao(dados, id_transacao):
    # devolve True se achou e excluiu
    for transacao in dados["transacoes"]:
        if transacao["id"] == id_transacao:
            dados["transacoes"].remove(transacao)
            return True
    return False


def resumo_do_mes(dados, mes):
    return {
        "nome_mes": nome_mes(mes),
        "totais": totais_do_mes(dados, mes),
        "gastos_por_categoria": gastos_por_categoria(dados, mes),
        "limites": situacao_limites(dados, mes),
    }

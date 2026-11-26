import os
import shutil
import tempfile
from datetime import date, timedelta

import requests

import armazenamento
import financas
import interpretador
from app import app

# data fixa para os testes não dependerem do dia em que forem rodados
HOJE = date(2026, 11, 25)


def criar_dados_teste():
    # dados pequenos, com as contas feitas à mão nos comentários dos testes
    return {
        "transacoes": [
            {"id": 1, "tipo": "entrada", "valor": 100000, "categoria": "entrada", "descricao": "recebi 1000 de salario", "data": "2026-11-05"},
            {"id": 2, "tipo": "gasto", "valor": 3500, "categoria": "alimentacao", "descricao": "gastei 35 no ifood", "data": "2026-11-10"},
            {"id": 3, "tipo": "gasto", "valor": 4590, "categoria": "alimentacao", "descricao": "gastei 45,90 no mercado", "data": "2026-11-12"},
            {"id": 4, "tipo": "gasto", "valor": 20000, "categoria": "transporte", "descricao": "paguei 200 de gasolina", "data": "2026-11-15"},
            {"id": 5, "tipo": "gasto", "valor": 9999, "categoria": "lazer", "descricao": "paguei 99,99 no show", "data": "2026-10-30"},
        ],
        "limites": {"alimentacao": 10000, "transporte": 15000, "lazer": 5000},
        "metas": [
            {"id": 1, "nome": "Viagem", "alvo": 100000, "guardado": 25000, "prazo": "2027-02-01"},
        ],
    }


def conferir_frase(frase, tipo, valor, categoria, data):
    resultado = interpretador.interpretar_frase(frase, HOJE)
    esperado = {"tipo": tipo, "valor": valor, "categoria": categoria, "data": data, "descricao": frase}
    if resultado != esperado:
        print("Falhou:", frase)
        print("  esperado:", esperado)
        print("  veio:    ", resultado)
    assert resultado == esperado


def testar_valores():
    assert interpretador.converter_valor("35") == 3500
    assert interpretador.converter_valor("35,90") == 3590
    assert interpretador.converter_valor("35.90") == 3590
    assert interpretador.converter_valor("35,9") == 3590
    assert interpretador.converter_valor("r$35") == 3500
    assert interpretador.converter_valor("1.200,50") == 120050
    assert interpretador.converter_valor("1.200") == 120000
    assert interpretador.converter_valor("ifood") is None
    assert interpretador.converter_valor("r$") is None
    assert interpretador.converter_valor("12,345") is None
    print("Valores: ok")


def testar_interpretador():
    conferir_frase("gastei 35 no ifood", "gasto", 3500, "alimentacao", "2026-11-25")
    conferir_frase("paguei 12,50 de uber ontem", "gasto", 1250, "transporte", "2026-11-24")
    conferir_frase("recebi 800 da bolsa", "entrada", 80000, "entrada", "2026-11-25")
    conferir_frase("comprei um tênis de r$ 1.200,50", "gasto", 120050, "compras", "2026-11-25")
    conferir_frase("gastei 35.90 no mercado anteontem", "gasto", 3590, "alimentacao", "2026-11-23")
    conferir_frase("r$42 de pizza", "gasto", 4200, "alimentacao", "2026-11-25")
    conferir_frase("ganhei 50 de mesada", "entrada", 5000, "entrada", "2026-11-25")
    conferir_frase("recebi meu salário de 1.500", "entrada", 150000, "entrada", "2026-11-25")
    conferir_frase("Paguei 450 de ALUGUEL", "gasto", 45000, "moradia", "2026-11-25")
    conferir_frase("comprei remédios na farmácia por 23,90", "gasto", 2390, "saude", "2026-11-25")
    conferir_frase("comprei uma bolsa de 150", "gasto", 15000, "compras", "2026-11-25")
    conferir_frase("paguei 30 no cinema.", "gasto", 3000, "lazer", "2026-11-25")
    conferir_frase("comprei um livro de 45,5", "gasto", 4550, "educacao", "2026-11-25")
    conferir_frase("fiz compras no mercado de 200", "gasto", 20000, "alimentacao", "2026-11-25")
    conferir_frase("gastei 20 com coisas", "gasto", 2000, "outros", "2026-11-25")

    # mais de um número: vale o que vem depois de "r$", "por", "de", "custou", "deu" ou "foi"
    conferir_frase("comprei 2 camisas por 90", "gasto", 9000, "compras", "2026-11-25")
    conferir_frase("comprei 2 livros de 45", "gasto", 4500, "educacao", "2026-11-25")
    conferir_frase("comprei 2 camisas r$90", "gasto", 9000, "compras", "2026-11-25")
    conferir_frase("a pizza deu 60 pra 3 pessoas", "gasto", 6000, "alimentacao", "2026-11-25")
    conferir_frase("o uber foi 23", "gasto", 2300, "transporte", "2026-11-25")
    conferir_frase("o almoço custou 25 com 2 sucos", "gasto", 2500, "alimentacao", "2026-11-25")
    # nenhum número depois dessas palavras: vale o primeiro
    conferir_frase("gastei 35 no ifood dia 3", "gasto", 3500, "alimentacao", "2026-11-25")
    # "como" no meio da frase não atrapalha
    conferir_frase("comprei um presente como lembrança por 50", "gasto", 5000, "compras", "2026-11-25")

    # frases com erro
    sem_valor = interpretador.interpretar_frase("gastei no mercado", HOJE)
    assert "erro" in sem_valor
    assert "valor" in sem_valor["erro"]
    valor_zero = interpretador.interpretar_frase("paguei 0 de uber", HOJE)
    assert "erro" in valor_zero
    assert "maior que zero" in valor_zero["erro"]
    assert "erro" in interpretador.interpretar_frase("paguei 0,00 de taxa", HOJE)
    assert "erro" in interpretador.interpretar_frase("   ", HOJE)

    # "ontem" no dia 1 volta para o mês anterior
    virada = interpretador.interpretar_frase("gastei 10 de onibus ontem", date(2026, 12, 1))
    assert virada["data"] == "2026-11-30"
    print("Interpretador: 28 frases ok")


def testar_confirmacao():
    gasto = interpretador.interpretar_frase("gastei 35 no ifood", HOJE)
    assert interpretador.texto_confirmacao(gasto, HOJE) == "Entendi: gasto de R$ 35,00 em Alimentação, hoje. Confirmar?"
    uber = interpretador.interpretar_frase("paguei 12,50 de uber ontem", HOJE)
    assert interpretador.texto_confirmacao(uber, HOJE) == "Entendi: gasto de R$ 12,50 em Transporte, ontem. Confirmar?"
    bolsa = interpretador.interpretar_frase("recebi 800 da bolsa", HOJE)
    assert interpretador.texto_confirmacao(bolsa, HOJE) == "Entendi: entrada de R$ 800,00, hoje. Confirmar?"
    print("Confirmação: ok")


def testar_perguntas():
    dados = criar_dados_teste()
    resposta = interpretador.responder_pergunta("quanto gastei com transporte esse mês?", dados, HOJE)
    assert resposta == "Em novembro de 2026 você gastou R$ 200,00 com Transporte. Seu limite é R$ 150,00 e você já usou 133%."

    resposta = interpretador.responder_pergunta("qual meu saldo?", dados, HOJE)
    assert resposta == "Em novembro de 2026 você recebeu R$ 1.000,00 e gastou R$ 280,90. Seu saldo do mês é R$ 719,10."

    resposta = interpretador.responder_pergunta("como estão minhas metas?", dados, HOJE)
    assert resposta == "Viagem: R$ 250,00 de R$ 1.000,00 (25%). Faltam R$ 750,00, então guarde R$ 250,00 por mês até 01/02/2027."

    # sem categoria: total do mês (3500 + 4590 + 20000 = 28090)
    resposta = interpretador.responder_pergunta("quanto gastei esse mês?", dados, HOJE)
    assert resposta == "Em novembro de 2026 você gastou R$ 280,90 no total."

    # sem "?" e sem valor, mas com "quanto": continua sendo pergunta
    resposta = interpretador.responder_pergunta("me diz quanto gastei", dados, HOJE)
    assert resposta == "Em novembro de 2026 você gastou R$ 280,90 no total."
    resposta = interpretador.responder_pergunta("quanto gastei com uber", dados, HOJE)
    assert resposta == "Em novembro de 2026 você gastou R$ 200,00 com Transporte. Seu limite é R$ 150,00 e você já usou 133%."

    # frase de gasto não é pergunta, mesmo com "como" no meio
    assert interpretador.responder_pergunta("gastei 35 no ifood", dados, HOJE) is None
    assert interpretador.responder_pergunta("comprei um presente como lembrança por 50", dados, HOJE) is None
    assert "Não entendi" in interpretador.responder_pergunta("qual a cor do céu?", dados, HOJE)
    print("Perguntas: ok")


def testar_formatacao():
    assert financas.formatar_reais(0) == "R$ 0,00"
    assert financas.formatar_reais(5) == "R$ 0,05"
    assert financas.formatar_reais(3590) == "R$ 35,90"
    assert financas.formatar_reais(123456) == "R$ 1.234,56"
    assert financas.formatar_reais(100000000) == "R$ 1.000.000,00"
    assert financas.formatar_reais(-1500) == "-R$ 15,00"
    assert financas.formatar_data("2026-11-25") == "25/11/2026"
    assert financas.nome_mes("2026-11") == "novembro de 2026"
    assert financas.nome_categoria("saude") == "Saúde"
    print("Formatação: ok")


def testar_calculos():
    dados = criar_dados_teste()

    # novembro: entradas 100000; gastos 3500 + 4590 + 20000 = 28090; saldo 71910
    # o show de outubro (9999) não entra
    totais = financas.totais_do_mes(dados, "2026-11")
    assert totais == {"entradas": 100000, "gastos": 28090, "saldo": 71910}
    assert financas.gastos_por_categoria(dados, "2026-11") == {"alimentacao": 8090, "transporte": 20000}
    assert financas.totais_do_mes(dados, "2026-10") == {"entradas": 0, "gastos": 9999, "saldo": -9999}

    # alimentação: 8090 de 10000 = 80% -> alerta
    # transporte: 20000 de 15000 = 133% -> estourou
    # lazer: 0 em novembro -> ok
    limites = financas.situacao_limites(dados, "2026-11")
    assert len(limites) == 3
    assert limites[0]["categoria"] == "alimentacao"
    assert limites[0]["porcentagem"] == 80
    assert limites[0]["situacao"] == "alerta"
    assert limites[1]["porcentagem"] == 133
    assert limites[1]["situacao"] == "estourou"
    assert "passou do limite de Transporte" in limites[1]["aviso"]
    assert limites[2]["gasto"] == 0
    assert limites[2]["situacao"] == "ok"
    assert limites[2]["aviso"] == ""
    assert financas.verificar_limite(dados, "saude", "2026-11") is None

    # 8090 de 10200 = 79,3%, que vira 79: ainda está ok
    dados["limites"]["alimentacao"] = 10200
    assert financas.verificar_limite(dados, "alimentacao", "2026-11")["porcentagem"] == 79
    assert financas.verificar_limite(dados, "alimentacao", "2026-11")["situacao"] == "ok"
    print("Totais e limites: ok")


def testar_metas():
    dados = criar_dados_teste()

    # Viagem: falta 100000 - 25000 = 75000
    # de 25/11/2026 até 01/02/2027 são 3 meses (dez, jan, fev) -> 75000 / 3 = 25000
    progresso = financas.progresso_meta(dados["metas"][0], HOJE)
    assert progresso["porcentagem"] == 25
    assert progresso["falta"] == 75000
    assert progresso["meses_restantes"] == 3
    assert progresso["por_mes"] == 25000
    assert progresso["concluida"] == False

    # 100000 / 3 = 33333,33... arredonda para cima -> 33334
    meta = {"id": 2, "nome": "Fone", "alvo": 100000, "guardado": 0, "prazo": "2027-02-01"}
    assert financas.progresso_meta(meta, HOJE)["por_mes"] == 33334

    # prazo já passou: conta como 1 mês, então precisa guardar tudo que falta
    atrasada = {"id": 3, "nome": "Curso", "alvo": 50000, "guardado": 20000, "prazo": "2026-10-01"}
    assert financas.progresso_meta(atrasada, HOJE)["meses_restantes"] == 1
    assert financas.progresso_meta(atrasada, HOJE)["por_mes"] == 30000

    # meta do CLAUDE.md: Viagem, 1500 com 300 guardados, prazo julho de 2027
    # 8 meses (dez a jul) -> 120000 / 8 = 15000
    viagem = {"id": 4, "nome": "Viagem", "alvo": 150000, "guardado": 30000, "prazo": "2027-07-01"}
    assert financas.progresso_meta(viagem, HOJE)["por_mes"] == 15000

    nova = financas.criar_meta(dados, "Notebook", 300000, "2027-12-01")
    assert nova["id"] == 2
    assert nova["guardado"] == 0
    assert len(dados["metas"]) == 2

    # guardando 75000 na Viagem ela fica completa
    financas.guardar_na_meta(dados, 1, 75000)
    assert dados["metas"][0]["guardado"] == 100000
    assert financas.progresso_meta(dados["metas"][0], HOJE)["concluida"] == True
    assert financas.progresso_meta(dados["metas"][0], HOJE)["por_mes"] == 0
    assert financas.guardar_na_meta(dados, 99, 1000) is None
    print("Metas: ok")


def testar_alteracoes():
    dados = criar_dados_teste()

    nova = financas.adicionar_transacao(dados, "gasto", 1250, "transporte", "paguei 12,50 de uber", "2026-11-25")
    assert nova["id"] == 6
    assert len(dados["transacoes"]) == 6
    assert financas.totais_do_mes(dados, "2026-11")["gastos"] == 28090 + 1250

    assert financas.excluir_transacao(dados, 2) == True
    assert len(dados["transacoes"]) == 5
    assert financas.excluir_transacao(dados, 99) == False

    financas.definir_limite(dados, "saude", 8000)
    assert dados["limites"]["saude"] == 8000
    financas.definir_limite(dados, "saude", 0)
    assert "saude" not in dados["limites"]
    print("Adicionar, excluir e limites: ok")


def testar_armazenamento(pasta_temporaria):
    # arquivo corrompido: não pode travar, volta com dados vazios
    # e guarda uma cópia do arquivo quebrado em quebrado_corrompido.json
    quebrado = os.path.join(pasta_temporaria, "quebrado.json")
    with open(quebrado, "w", encoding="utf-8") as arquivo:
        arquivo.write("{ isso não é json")
    dados = armazenamento.carregar_dados(quebrado)
    assert dados == {"transacoes": [], "limites": {}, "metas": []}
    with open(os.path.join(pasta_temporaria, "quebrado_corrompido.json"), "r", encoding="utf-8") as arquivo:
        assert arquivo.read() == "{ isso não é json"

    # arquivo que não existe: é criado a partir do exemplo, já no mês atual
    novo = os.path.join(pasta_temporaria, "novo.json")
    dados = armazenamento.carregar_dados(novo)
    assert os.path.exists(novo)
    assert len(dados["transacoes"]) == 15
    mes_atual = financas.mes_de(date.today())
    for transacao in dados["transacoes"]:
        assert transacao["data"].startswith(mes_atual)
        assert transacao["data"] <= date.today().isoformat()

    # salvar e carregar de novo devolve a mesma coisa
    salvo = os.path.join(pasta_temporaria, "salvo.json")
    armazenamento.salvar_dados(criar_dados_teste(), salvo)
    assert armazenamento.carregar_dados(salvo) == criar_dados_teste()
    print("Armazenamento: ok")


def testar_mes_atual():
    # em 10/12/2026: o dia 05 continua 05, o dia 24 vira 10 (não pode passar de hoje)
    dados = {"transacoes": [{"data": "2026-11-05"}, {"data": "2026-11-24"}]}
    armazenamento.trazer_para_o_mes_atual(dados, date(2026, 12, 10))
    assert dados["transacoes"][0]["data"] == "2026-12-05"
    assert dados["transacoes"][1]["data"] == "2026-12-10"
    print("Exemplo no mês atual: ok")


def pagina(resposta):
    # o texto HTML que a rota devolveu
    assert resposta.status_code == 200
    return resposta.get_data(as_text=True)


def testar_rotas(pasta_temporaria):
    # o site usa um arquivo na pasta temporária, nunca o dados/trocado.json
    arquivo = os.path.join(pasta_temporaria, "trocado.json")
    app.config["ARQUIVO_DADOS"] = arquivo
    app.config["TESTING"] = True
    # sem chave, mesmo que exista um .env com chave nesta pasta
    app.config["GEMINI_CHAVE"] = ""
    cliente = app.test_client()
    hoje = date.today().isoformat()

    # cada página abre (e a primeira cria o arquivo a partir do exemplo)
    assert "Chat" in pagina(cliente.get("/"))
    assert "gastei 35 no ifood" in pagina(cliente.get("/transacoes"))
    assert "Alimentação" in pagina(cliente.get("/limites"))
    assert "Viagem" in pagina(cliente.get("/metas"))
    assert "Entradas" in pagina(cliente.get("/resumo"))
    assert len(armazenamento.carregar_dados(arquivo)["transacoes"]) == 15

    # frase: mostra a confirmação, mas ainda não salva
    texto = pagina(cliente.post("/", data={"mensagem": "gastei 35 no ifood"}))
    assert "Entendi: gasto de R$ 35,00 em Alimentação, hoje. Confirmar?" in texto
    assert 'name="valor" value="3500"' in texto
    assert "entendido pelas regras" in texto
    assert len(armazenamento.carregar_dados(arquivo)["transacoes"]) == 15

    # com uma chave falsa e um Gemini falso, o cartão diz que foi o Gemini
    funcao_verdadeira = interpretador.perguntar_ao_gemini

    def gemini_falso(frase, hoje, chave, modelo):
        return '{"tipo": "gasto", "valor": 35, "categoria": "alimentacao", "data": "' + hoje.isoformat() + '"}'

    interpretador.perguntar_ao_gemini = gemini_falso
    app.config["GEMINI_CHAVE"] = "chave-falsa"
    texto = pagina(cliente.post("/", data={"mensagem": "gastei 35 no ifood"}))
    assert "entendido pelo Gemini" in texto
    assert "chave-falsa" not in texto
    interpretador.perguntar_ao_gemini = funcao_verdadeira
    app.config["GEMINI_CHAVE"] = ""

    # confirmar trocando a categoria para lazer: lazer tinha 30 de 50, agora 65 de 50
    formulario = {"acao": "confirmar", "tipo": "gasto", "valor": "3500", "categoria": "lazer",
                  "data": hoje, "descricao": "gastei 35 no ifood"}
    texto = pagina(cliente.post("/confirmar", data=formulario, follow_redirects=True))
    assert "Registro salvo: gasto de R$ 35,00 em Lazer" in texto
    assert "passou do limite de Lazer" in texto
    dados = armazenamento.carregar_dados(arquivo)
    assert len(dados["transacoes"]) == 16
    assert dados["transacoes"][-1]["categoria"] == "lazer"
    assert dados["transacoes"][-1]["valor"] == 3500

    # entrada sempre fica com a categoria entrada
    formulario = {"acao": "confirmar", "tipo": "entrada", "valor": "80000", "categoria": "lazer",
                  "data": hoje, "descricao": "recebi 800 da bolsa"}
    texto = pagina(cliente.post("/confirmar", data=formulario, follow_redirects=True))
    assert "Registro salvo: entrada de R$ 800,00" in texto
    assert armazenamento.carregar_dados(arquivo)["transacoes"][-1]["categoria"] == "entrada"

    # cancelar não salva
    formulario = {"acao": "cancelar", "tipo": "gasto", "valor": "3500", "categoria": "lazer",
                  "data": hoje, "descricao": "gastei 35 no ifood"}
    assert "cancelado" in pagina(cliente.post("/confirmar", data=formulario, follow_redirects=True))
    assert len(armazenamento.carregar_dados(arquivo)["transacoes"]) == 17

    # perguntas
    assert "Seu saldo do mês é" in pagina(cliente.post("/", data={"mensagem": "qual meu saldo?"}))
    assert "com Transporte" in pagina(cliente.post("/", data={"mensagem": "quanto gastei com transporte esse mês?"}))

    # erros no chat
    assert "Não encontrei o valor" in pagina(cliente.post("/", data={"mensagem": "gastei no mercado"}))
    assert "maior que zero" in pagina(cliente.post("/", data={"mensagem": "paguei 0 de uber"}))
    assert "Escreva uma mensagem" in pagina(cliente.post("/", data={"mensagem": "   "}))

    # campos escondidos alterados: nada é salvo
    errados = [
        [{"tipo": "presente", "valor": "3500", "categoria": "lazer", "data": hoje}, "Tipo inválido"],
        [{"tipo": "gasto", "valor": "abc", "categoria": "lazer", "data": hoje}, "Valor inválido"],
        [{"tipo": "gasto", "valor": "-5", "categoria": "lazer", "data": hoje}, "Valor inválido"],
        [{"tipo": "gasto", "valor": "3500", "categoria": "viagem", "data": hoje}, "categoria válida"],
        [{"tipo": "gasto", "valor": "3500", "categoria": "lazer", "data": "2026-13-01"}, "Data inválida"],
    ]
    for item in errados:
        formulario = item[0]
        formulario["acao"] = "confirmar"
        assert item[1] in pagina(cliente.post("/confirmar", data=formulario))
    assert len(armazenamento.carregar_dados(arquivo)["transacoes"]) == 17

    # limites: "500,00" e "500" valem R$ 500,00; 0 tira o limite
    texto = pagina(cliente.post("/limites/definir", data={"categoria": "saude", "valor": "500,00"}, follow_redirects=True))
    assert "Limite de Saúde definido em R$ 500,00" in texto
    assert armazenamento.carregar_dados(arquivo)["limites"]["saude"] == 50000
    pagina(cliente.post("/limites/definir", data={"categoria": "moradia", "valor": "500"}, follow_redirects=True))
    assert armazenamento.carregar_dados(arquivo)["limites"]["moradia"] == 50000
    texto = pagina(cliente.post("/limites/definir", data={"categoria": "saude", "valor": "0"}, follow_redirects=True))
    assert "Limite de Saúde removido" in texto
    assert "saude" not in armazenamento.carregar_dados(arquivo)["limites"]

    assert "Digite um valor" in pagina(cliente.post("/limites/definir", data={"categoria": "lazer", "valor": ""}))
    assert "negativo" in pagina(cliente.post("/limites/definir", data={"categoria": "lazer", "valor": "-50"}))
    assert "Valor inválido" in pagina(cliente.post("/limites/definir", data={"categoria": "lazer", "valor": "abc"}))
    assert "categoria válida" in pagina(cliente.post("/limites/definir", data={"categoria": "viagem", "valor": "50"}))
    assert armazenamento.carregar_dados(arquivo)["limites"]["lazer"] == 5000

    # metas: criar e guardar dinheiro
    prazo = (date.today() + timedelta(days=90)).isoformat()
    texto = pagina(cliente.post("/metas/criar", data={"nome": "Show", "valor": "300", "prazo": prazo}, follow_redirects=True))
    assert "Meta Show criada" in texto
    meta = armazenamento.carregar_dados(arquivo)["metas"][-1]
    assert meta == {"id": 3, "nome": "Show", "alvo": 30000, "guardado": 0, "prazo": prazo}

    texto = pagina(cliente.post("/metas/guardar", data={"id": "3", "valor": "100"}, follow_redirects=True))
    assert "R$ 100,00 guardados na meta Show" in texto
    assert armazenamento.carregar_dados(arquivo)["metas"][-1]["guardado"] == 10000
    texto = pagina(cliente.post("/metas/guardar", data={"id": "3", "valor": "200,00"}, follow_redirects=True))
    assert "completou a meta" in texto

    ontem = (date.today() - timedelta(days=1)).isoformat()
    assert "nome da meta" in pagina(cliente.post("/metas/criar", data={"nome": "  ", "valor": "300", "prazo": prazo}))
    assert "maior que zero" in pagina(cliente.post("/metas/criar", data={"nome": "Show", "valor": "0", "prazo": prazo}))
    assert "Valor inválido" in pagina(cliente.post("/metas/criar", data={"nome": "Show", "valor": "trezentos", "prazo": prazo}))
    assert "prazo válido" in pagina(cliente.post("/metas/criar", data={"nome": "Show", "valor": "300", "prazo": "2026-02-30"}))
    assert "prazo válido" in pagina(cliente.post("/metas/criar", data={"nome": "Show", "valor": "300", "prazo": ""}))
    assert "depois de hoje" in pagina(cliente.post("/metas/criar", data={"nome": "Show", "valor": "300", "prazo": ontem}))
    assert "não existe" in pagina(cliente.post("/metas/guardar", data={"id": "99", "valor": "100"}))
    assert "Meta inválida" in pagina(cliente.post("/metas/guardar", data={"id": "abc", "valor": "100"}))
    assert "negativo" in pagina(cliente.post("/metas/guardar", data={"id": "1", "valor": "-10"}))
    assert "maior que zero" in pagina(cliente.post("/metas/guardar", data={"id": "1", "valor": "0"}))
    assert len(armazenamento.carregar_dados(arquivo)["metas"]) == 3

    # meta com prazo vencido mostra "Prazo vencido"
    dados = armazenamento.carregar_dados(arquivo)
    dados["metas"].append({"id": 4, "nome": "Atrasada", "alvo": 50000, "guardado": 1000, "prazo": "2026-01-01"})
    armazenamento.salvar_dados(dados, arquivo)
    assert "Prazo vencido" in pagina(cliente.get("/metas"))

    # excluir
    texto = pagina(cliente.post("/excluir", data={"id": "16"}, follow_redirects=True))
    assert "Registro excluído" in texto
    assert len(armazenamento.carregar_dados(arquivo)["transacoes"]) == 16
    assert "não existe" in pagina(cliente.post("/excluir", data={"id": "16"}))
    assert "Registro inválido" in pagina(cliente.post("/excluir", data={"id": "abc"}))

    # resumo com seletor de mês
    mes_atual = financas.mes_de(date.today())
    assert financas.nome_mes(mes_atual) in pagina(cliente.get("/resumo?mes=" + mes_atual))
    assert "janeiro de 2025" in pagina(cliente.get("/resumo?mes=2025-01"))
    assert "Mês inválido" in pagina(cliente.get("/resumo?mes=abc"))
    assert "Mês inválido" in pagina(cliente.get("/resumo?mes=2026-13"))
    print("Rotas: ok")


def testar_validacao_gemini():
    frase = "gastei 35,90 no ifood"

    # JSON certo: o valor em reais vira centavos
    texto = '{"tipo": "gasto", "valor": 35.9, "categoria": "alimentacao", "data": "2026-11-25"}'
    assert interpretador.validar_resposta_gemini(texto, frase) == {
        "tipo": "gasto", "valor": 3590, "categoria": "alimentacao", "data": "2026-11-25", "descricao": frase}
    texto = '{"tipo": "gasto", "valor": 19.99, "categoria": "lazer", "data": "2026-11-24"}'
    assert interpretador.validar_resposta_gemini(texto, frase)["valor"] == 1999
    # entrada sempre fica com a categoria "entrada"
    texto = '{"tipo": "entrada", "valor": 800, "categoria": "outros", "data": "2026-11-25"}'
    entrada = interpretador.validar_resposta_gemini(texto, "recebi 800 da bolsa")
    assert entrada["valor"] == 80000
    assert entrada["categoria"] == "entrada"

    # respostas erradas: devolve None
    errados = [
        '{"tipo": "gasto", "valor": ',
        "não é json",
        "[1, 2, 3]",
        '{"tipo": "gasto", "valor": 0, "categoria": "lazer", "data": "2026-11-25"}',
        '{"tipo": "gasto", "valor": -10, "categoria": "lazer", "data": "2026-11-25"}',
        '{"tipo": "gasto", "valor": 0.001, "categoria": "lazer", "data": "2026-11-25"}',
        '{"tipo": "gasto", "valor": "35", "categoria": "lazer", "data": "2026-11-25"}',
        '{"tipo": "gasto", "valor": true, "categoria": "lazer", "data": "2026-11-25"}',
        '{"tipo": "gasto", "valor": 35, "categoria": "comida", "data": "2026-11-25"}',
        '{"tipo": "gasto", "valor": 35, "data": "2026-11-25"}',
        '{"tipo": "transferencia", "valor": 35, "categoria": "lazer", "data": "2026-11-25"}',
        '{"tipo": "gasto", "valor": 35, "categoria": "lazer", "data": "25/11/2026"}',
        '{"tipo": "gasto", "valor": 35, "categoria": "lazer", "data": "2026-02-30"}',
        '{"tipo": "gasto", "valor": 35, "categoria": "lazer"}',
    ]
    for texto in errados:
        if interpretador.validar_resposta_gemini(texto, frase) is not None:
            print("Deveria ser inválido:", texto)
        assert interpretador.validar_resposta_gemini(texto, frase) is None
    print("Validação do Gemini: ok")


def testar_escolha_do_interpretador():
    # sem chave: usa as regras e não chama a internet
    resultado = interpretador.interpretar("gastei 35 no ifood", HOJE, "", interpretador.MODELO_PADRAO)
    assert resultado["origem"] == "regras"
    assert resultado["valor"] == 3500
    assert resultado["categoria"] == "alimentacao"
    assert interpretador.interpretar("gastei no mercado", HOJE, "", "")["origem"] == "regras"

    # com chave, troco a função que usa a internet por funções falsas
    funcao_verdadeira = interpretador.perguntar_ao_gemini

    def gemini_certo(frase, hoje, chave, modelo):
        return '{"tipo": "gasto", "valor": 50, "categoria": "compras", "data": "2026-11-25"}'

    def gemini_quebrado(frase, hoje, chave, modelo):
        return '{"tipo": "gasto", "valor": '

    def gemini_sem_internet(frase, hoje, chave, modelo):
        raise requests.ConnectionError("sem internet")

    interpretador.perguntar_ao_gemini = gemini_certo
    resultado = interpretador.interpretar("comprei um presente de 50", HOJE, "chave-falsa", "modelo")
    assert resultado["origem"] == "gemini"
    assert resultado["valor"] == 5000

    # resposta quebrada ou erro de internet: volta para as regras
    interpretador.perguntar_ao_gemini = gemini_quebrado
    resultado = interpretador.interpretar("gastei 35 no ifood", HOJE, "chave-falsa", "modelo")
    assert resultado["origem"] == "regras"
    assert resultado["valor"] == 3500

    interpretador.perguntar_ao_gemini = gemini_sem_internet
    resultado = interpretador.interpretar("gastei 35 no ifood", HOJE, "chave-falsa", "modelo")
    assert resultado["origem"] == "regras"
    assert resultado["categoria"] == "alimentacao"

    interpretador.perguntar_ao_gemini = funcao_verdadeira
    print("Escolha entre Gemini e regras: ok")


def conteudo_da_pasta_dados():
    # nome e conteúdo de cada arquivo, para ver se os testes mudaram alguma coisa
    pasta = os.path.join(armazenamento.PASTA, "dados")
    conteudo = {}
    for nome in os.listdir(pasta):
        with open(os.path.join(pasta, nome), "rb") as arquivo:
            conteudo[nome] = arquivo.read()
    return conteudo


# os testes usam uma pasta temporária, que é apagada no final
antes = conteudo_da_pasta_dados()
pasta_temporaria = tempfile.mkdtemp()

testar_valores()
testar_interpretador()
testar_confirmacao()
testar_perguntas()
testar_formatacao()
testar_calculos()
testar_metas()
testar_alteracoes()
testar_armazenamento(pasta_temporaria)
testar_mes_atual()
testar_validacao_gemini()
testar_escolha_do_interpretador()
testar_rotas(pasta_temporaria)

shutil.rmtree(pasta_temporaria)
assert conteudo_da_pasta_dados() == antes
print("Pasta dados/ sem alterações: ok")
print()
print("Todos os testes passaram.")

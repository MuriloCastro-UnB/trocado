import os
from datetime import date

import armazenamento
import financas
import interpretador

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


def testar_armazenamento():
    pasta_dados = os.path.join(armazenamento.PASTA, "dados")

    # arquivo corrompido: não pode travar, volta com dados vazios
    # e guarda uma cópia do arquivo quebrado em teste_quebrado_corrompido.json
    quebrado = os.path.join(pasta_dados, "teste_quebrado.json")
    copia = os.path.join(pasta_dados, "teste_quebrado_corrompido.json")
    with open(quebrado, "w", encoding="utf-8") as arquivo:
        arquivo.write("{ isso não é json")
    dados = armazenamento.carregar_dados(quebrado)
    with open(copia, "r", encoding="utf-8") as arquivo:
        conteudo_copia = arquivo.read()
    os.remove(quebrado)
    os.remove(copia)
    assert dados == {"transacoes": [], "limites": {}, "metas": []}
    assert conteudo_copia == "{ isso não é json"

    # arquivo que não existe: é criado a partir do exemplo
    novo = os.path.join(pasta_dados, "teste_novo.json")
    dados = armazenamento.carregar_dados(novo)
    criou = os.path.exists(novo)
    os.remove(novo)
    assert criou
    assert len(dados["transacoes"]) == 15

    # salvar e carregar de novo devolve a mesma coisa
    salvo = os.path.join(pasta_dados, "teste_salvo.json")
    armazenamento.salvar_dados(criar_dados_teste(), salvo)
    dados = armazenamento.carregar_dados(salvo)
    os.remove(salvo)
    assert dados == criar_dados_teste()
    print("Armazenamento: ok")


testar_valores()
testar_interpretador()
testar_confirmacao()
testar_perguntas()
testar_formatacao()
testar_calculos()
testar_metas()
testar_alteracoes()
testar_armazenamento()
print()
print("Todos os testes passaram.")

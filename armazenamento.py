import json
import os
import shutil
from datetime import date

PASTA = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_DADOS = os.path.join(PASTA, "dados", "trocado.json")
ARQUIVO_EXEMPLO = os.path.join(PASTA, "dados", "exemplo.json")


def dados_vazios():
    return {"transacoes": [], "limites": {}, "metas": []}


def guardar_corrompido(caminho):
    # guarda uma cópia do arquivo quebrado para os dados antigos não se perderem
    # trocado.json vira trocado_corrompido.json
    copia = caminho.replace(".json", "_corrompido.json")
    shutil.copy(caminho, copia)
    print("Aviso: o arquivo", caminho, "está corrompido.")
    print("Uma cópia dele foi salva em", copia)
    print("Começando com dados vazios.")
    return dados_vazios()


def trazer_para_o_mes_atual(dados, hoje):
    # os exemplos são de novembro de 2026: troca o ano e o mês pelos de hoje
    # para o resumo e os limites não aparecerem vazios
    for transacao in dados["transacoes"]:
        dia = int(transacao["data"][8:10])
        if dia > hoje.day:
            dia = hoje.day
        transacao["data"] = date(hoje.year, hoje.month, dia).isoformat()


def criar_a_partir_do_exemplo(caminho, caminho_exemplo):
    with open(caminho_exemplo, "r", encoding="utf-8") as arquivo:
        dados = json.load(arquivo)
    trazer_para_o_mes_atual(dados, date.today())
    salvar_dados(dados, caminho)


def carregar_dados(caminho=ARQUIVO_DADOS, caminho_exemplo=ARQUIVO_EXEMPLO):
    # na primeira execução o arquivo de uso ainda não existe: cria a partir do exemplo
    if not os.path.exists(caminho):
        if not os.path.exists(caminho_exemplo):
            return dados_vazios()
        criar_a_partir_do_exemplo(caminho, caminho_exemplo)

    try:
        with open(caminho, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
    except ValueError:
        return guardar_corrompido(caminho)

    if type(dados) != dict:
        return guardar_corrompido(caminho)

    # se faltar alguma parte no arquivo, completa com a parte vazia
    vazios = dados_vazios()
    for chave in vazios:
        if chave not in dados:
            dados[chave] = vazios[chave]
    return dados


def salvar_dados(dados, caminho=ARQUIVO_DADOS):
    with open(caminho, "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=2)

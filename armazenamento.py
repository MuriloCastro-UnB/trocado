import json
import os
import shutil

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


def carregar_dados(caminho=ARQUIVO_DADOS, caminho_exemplo=ARQUIVO_EXEMPLO):
    # na primeira execução o arquivo de uso ainda não existe: copia o exemplo
    if not os.path.exists(caminho):
        if not os.path.exists(caminho_exemplo):
            return dados_vazios()
        shutil.copy(caminho_exemplo, caminho)

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

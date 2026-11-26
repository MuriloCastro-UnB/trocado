# Trocado

## Descrição

Trabalho final de Computação para Engenharia (ENE0334), 2º semestre de 2026, na UnB.

- Aluno: Murilo Silva Braga de Castro
- Matrícula: 262006172

O Trocado é um site para controlar o próprio dinheiro conversando. Anotar cada gasto numa planilha dá trabalho, e por isso muita gente desiste de controlar o dinheiro. A ideia é escrever do jeito que a gente fala, como "gastei 35 no ifood", e o programa entender e guardar.

Funcionalidades principais:

- **Chat:** escrevo um gasto ou uma entrada ("paguei 12,50 de uber ontem", "recebi 800 da bolsa"). O programa mostra o que entendeu (tipo, valor, categoria e data) e só salva depois que eu confirmo. Também respondo perguntas como "qual meu saldo?", "quanto gastei com transporte esse mês?" e "como estão minhas metas?".
- **Limites por categoria:** defino um limite mensal para cada categoria e o programa avisa quando passo de 80% e quando estouro.
- **Metas de economia:** crio uma meta com nome, valor e prazo, registro quanto guardei e vejo o progresso e quanto preciso guardar por mês.
- **Resumo do mês:** entradas, gastos, saldo, gastos por categoria e situação dos limites, com escolha do mês.
- **Lista de transações:** vejo os registros do mês e posso excluir.

O que o programa recebe, processa e apresenta:

- **Recebe** frases em português digitadas no chat e os dados dos formulários (limites e metas).
- **Processa** a frase com um interpretador que eu escrevi em Python. Ele acha o valor, decide se é gasto ou entrada, descobre a categoria por palavras-chave e entende "hoje", "ontem" e "anteontem". Como opção, a frase pode ser interpretada pela API do Gemini. Os cálculos de saldo, limites, metas e resumo são feitos em Python, e os dados ficam salvos num arquivo JSON.
- **Apresenta** páginas web com a confirmação do que foi entendido, respostas às perguntas, avisos de limite, barras de progresso e o resumo do mês.

## Requisitos

- Python 3.10 ou mais novo. As bibliotecas pedem no mínimo o 3.10, e eu usei o Python 3.15.2.
- Git (usei a versão 2.56.0).
- Bibliotecas, que estão no `requirements.txt`:
  - Flask 3.1.3, para o site;
  - requests 2.34.2, para chamar a API do Gemini;
  - python-dotenv 1.2.4, para ler o arquivo `.env`.
- Sistema em que testei: Windows 11 Pro, versão 25H2.
- Arquivo principal: `app.py`.

Arquivos e pastas:

| Caminho | O que tem |
|---|---|
| `app.py` | rotas e páginas do Flask (é o arquivo que se executa) |
| `interpretador.py` | entende as frases do chat (regras e Gemini) e responde as perguntas |
| `financas.py` | cálculos: totais do mês, gastos por categoria, limites, metas e resumo |
| `armazenamento.py` | lê e grava o arquivo JSON com os dados |
| `testes.py` | testes com `assert` |
| `templates/` | páginas HTML (base, chat, transações, limites, metas, resumo) |
| `static/` | `estilo.css` e os ícones em `static/icones/` |
| `dados/` | `exemplo.json` com dados de exemplo; o `trocado.json` é criado aqui quando o programa roda |
| `.env.example` | modelo da configuração do Gemini, sem chave |
| `requirements.txt` | bibliotecas e versões |

## Clonagem

```
git clone https://github.com/MuriloCastro-UnB/trocado.git
cd trocado
```

## Instalação

Primeiro crie e ative o ambiente virtual (a pasta `.venv`). Escolha o comando do seu sistema:

**Windows (PowerShell)**

```
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Windows (cmd)**

```
python -m venv .venv
.venv\Scripts\activate.bat
```

**macOS ou Linux**

```
python3 -m venv .venv
source .venv/bin/activate
```

Com o ambiente ativado, aparece `(.venv)` no começo da linha do terminal. Depois instale as bibliotecas:

```
python -m pip install -r requirements.txt
```

Se o PowerShell der um erro dizendo que a execução de scripts foi desabilitada neste sistema, é a política de segurança do Windows bloqueando o `Activate.ps1`. Para liberar só nessa janela do terminal, rode o comando abaixo e depois ative de novo:

```
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

Essa liberação vale só até fechar a janela. Outra saída é usar o cmd em vez do PowerShell.

## Execução e uso

Com o ambiente virtual ativado, dentro da pasta `trocado`:

```
python app.py
```

Depois abra no navegador o endereço http://127.0.0.1:5000/

Para parar o programa, aperte Ctrl+C no terminal.

Páginas do site:

| Rota | Página |
|---|---|
| `/` | Chat |
| `/transacoes` | Transações do mês, com botão de excluir |
| `/limites` | Limites por categoria |
| `/metas` | Metas de economia |
| `/resumo` | Resumo do mês |

### Exemplo de uso

Na primeira execução o programa já vem com dados de exemplo (veja a próxima seção). No chat, digite:

```
gastei 35 no ifood
```

e clique em Enviar. Aparece um cartão de confirmação:

```
R$ 35,00
Entendi: gasto de R$ 35,00 em Alimentação, hoje. Confirmar?
entendido pelas regras
```

Dá para trocar a categoria nesse cartão antes de confirmar. Ao clicar em Confirmar, o gasto é salvo e aparece:

```
Registro salvo: gasto de R$ 35,00 em Alimentação, 25/11/2026.
Cuidado: você já usou 97% do limite de Alimentação (R$ 233,10 de R$ 240,00).
```

A data é a do dia em que o programa está rodando. O aviso aparece porque nos dados de exemplo Alimentação já tinha R$ 198,10 de um limite de R$ 240,00. O gasto também passa a aparecer em "Últimos registros", na página Transações e no Resumo.

Depois, perguntando no chat:

```
qual meu saldo?
```

a resposta é:

```
Em novembro de 2026 você recebeu R$ 1.100,00 e gastou R$ 922,40. Seu saldo do mês é R$ 177,60.
```

O mês da resposta é sempre o mês atual do computador.

## Arquivos e configurações

### Dados

Os dados ficam em `dados/trocado.json`. Esse arquivo não vai para o GitHub (está no `.gitignore`). Na primeira vez que o programa roda, ele cria o `trocado.json` a partir do `dados/exemplo.json`. Os exemplos são de novembro de 2026, então na cópia eu troco o mês e o ano de cada transação pelos atuais, para o resumo e os limites não aparecerem vazios.

Para recomeçar do zero com os dados de exemplo, pare o programa e apague o `dados/trocado.json`. Ele é criado de novo na próxima execução.

Se o `trocado.json` estiver corrompido, o programa não trava. Ele guarda uma cópia em `dados/trocado_corrompido.json`, avisa no terminal e começa com os dados vazios.

### Gemini (opcional)

O programa funciona sem nenhuma configuração. Sem a chave, as frases são entendidas pelo meu interpretador por regras. Com uma chave do Gemini, a frase é enviada para a IA, que devolve tipo, valor, categoria e data, e o programa confere a resposta antes de usar. Se não houver internet, se a chave estiver errada, se acabar o limite de uso ou se a resposta vier errada, ele volta a usar as regras. As perguntas e todos os cálculos continuam sendo feitos em Python.

Para usar o Gemini:

1. Crie uma chave em https://aistudio.google.com/apikey (botão "Create API key"), entrando com uma conta Google.
2. Copie o arquivo `.env.example` para `.env`:
   - Windows: `copy .env.example .env`
   - macOS ou Linux: `cp .env.example .env`
3. Abra o `.env` e cole a chave depois do `=`, sem aspas:

```
GEMINI_API_KEY=sua_chave_aqui
GEMINI_MODELO=gemini-3.5-flash-lite
```

4. Rode `python app.py` de novo. O terminal mostra se o Gemini está ligado, e o cartão de confirmação mostra "entendido pelo Gemini" ou "entendido pelas regras".

O `.env` está no `.gitignore` para a chave nunca ir para o GitHub.

## Testes

Com o ambiente virtual ativado, dentro da pasta `trocado`:

```
python testes.py
```

Os testes conferem:

- o interpretador com várias frases;
- os cálculos, com resultados conferidos à mão;
- a validação das respostas do Gemini, com respostas falsas e sem usar a internet;
- todas as páginas do site.

Eles usam uma pasta temporária e não mexem na pasta `dados/`. No final aparece "Todos os testes passaram."

## Verificação da entrega

Para conferir se o projeto funciona do zero, clonei o repositório numa pasta nova e segui este README desde a clonagem.

- Data do teste: 25/11/2026
- Sistema operacional: Windows 11 Pro, versão 25H2, no PowerShell
- Versão do Python: 3.15.2
- Pasta onde clonei: uma pasta nova, separada da que eu uso para programar
- Passos seguidos: os deste README, desde o `git clone`. No PowerShell, a ativação do ambiente virtual deu o erro de execução de scripts, e resolvi com o `Set-ExecutionPolicy` que está na seção Instalação. A instalação pelo `requirements.txt` funcionou com as mesmas versões.
- Resultado de `python testes.py`: "Todos os testes passaram."
- Exemplo usado: sem chave do Gemini, digitei "gastei 35 no ifood" no chat e confirmei.
- Resultado obtido: o cartão mostrou "Entendi: gasto de R$ 35,00 em Alimentação, hoje. Confirmar?" com "entendido pelas regras". Depois de confirmar, apareceu "Registro salvo: gasto de R$ 35,00 em Alimentação, 25/11/2026." e o aviso de 97% do limite de Alimentação, igual ao exemplo de uso.

# 0006 — Sem efeitos colaterais em tempo de importação

- **Status:** Aceita
- **Data:** 2026-08-12
- **Decidido por:** Alan M

## Contexto

[`virus_hunter.py`](../../script/virus_hunter.py) executava, no nível do módulo:

```python
SI=serverInfo()
print SI
```

`serverInfo()` roda `os.system('rm server.info')` e abre conexões SSH para os 20 nós do
cluster para coletar CPU e RAM. Estando em nível de módulo, isso acontecia **ao importar o
arquivo** — não ao executá-lo.

Três consequências:

1. **Nenhuma parte do arquivo podia ser importada, testada ou inspecionada** sem o cluster
   original, que hoje provavelmente não existe mais. Isso bloqueava toda a infraestrutura
   de validação proposta em [`known-issues.md`](../known-issues.md) (item K10).
2. **O alcance ia além do próprio arquivo.** [`firstpage.py:68`](../../script/firstpage.py#L68)
   faz `from virus_hunter import readSeeds2` no nível do módulo, e `firstpage.py` é a etapa
   final de relatório dos pipelines gerados pelos **dois** orquestradores. Ou seja, o
   pipeline de `readseeds2.py` também herdava o SSH — o que corrige a suposição, registrada
   antes, de que `readseeds2.py` seria independente do cluster.
3. Provavelmente explica por que o trabalho anterior do grupo (jan/2025) avançou apenas até
   a geração de scripts.

Com `virus_hunter.py` fixado como referência ([ADR-0004](0004-virus-hunter-as-reference.md)),
remover esse efeito passou a ser pré-requisito de qualquer trabalho de validação.

## Alternativas consideradas

**Chamar `serverInfo()` sob demanda, só quando `SI` for necessário.** `SI` é usado apenas
em `trinity()` ([1680-1681](../../script/virus_hunter.py#L1680-L1681)), então o pipeline
poderia ser gerado sem cluster nas configurações que não usam SPAdes. Descartada por
enquanto: `trinity('')` é chamado incondicionalmente, e adiar a chamada mudaria o momento
em que a verificação de nós indisponíveis aborta a execução — alteração de comportamento,
não refatoração.

**Substituir a detecção por configuração declarativa.** É o destino desejado (o teto de
memória do SPAdes derivado do nó é a causa de [K7](../known-issues.md), não-determinismo).
Descartada agora: altera comportamento científico e exige ADR própria.

**Mover a chamada para o início de `__main__`.** Preserva exatamente a ordem de execução —
antes rodava no import, ou seja, antes de qualquer coisa do `__main__` — e não altera
comportamento algum de quem executa o script.

## Decisão

Mover `SI=serverInfo()` e `print SI` para a primeira posição do bloco
`if __name__ == "__main__":`.

Adotar como regra do projeto: **nenhum módulo deve produzir efeito colateral ao ser
importado.** A regra é verificada por
[`tests/check_no_import_side_effects.py`](../../tests/check_no_import_side_effects.py).

## Consequências

- `virus_hunter.py` passa a ser importável sem cluster. `firstpage.py` deixa de disparar
  SSH ao ser carregado.
- **Nada muda para quem executa `python virus_hunter.py`**: a chamada ocorre no mesmo ponto
  da sequência, com a mesma saída.
- Surge o primeiro teste executável do repositório. Ele roda em Python 3, embora o código
  verificado seja Python 2, porque é lexical e nunca importa o alvo — necessário, já que
  Python 2 não está disponível nas máquinas atuais.
- **Validação realizada:** o verificador foi executado contra a versão anterior do arquivo
  (`git show master:script/virus_hunter.py`), onde **falha** apontando a linha 205, e
  contra a versão corrigida, onde **passa**. Um teste que não falha no código defeituoso
  não valida nada; a primeira versão do verificador de fato não falhava — um `^` sem
  `re.MULTILINE` deixava vazia a lista de funções — e o defeito só apareceu por causa dessa
  conferência.
- O verificador não segue imports: checa cada arquivo isoladamente. Módulos relevantes
  precisam ser passados explicitamente.
- Permanece pendente a causa de fundo: o teto de memória do SPAdes continua derivado do nó
  de execução ([K7](../known-issues.md)). Esta ADR não trata disso.

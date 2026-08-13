# 0003 — Orquestrador canônico

- **Status:** **Substituída por [ADR-0004](0004-virus-hunter-as-reference.md)**
- **Data:** 2026-08-12
- **Decidido por:** Alan M

> **Resolvida.** A evidência listada na seção final foi levantada e apontou para
> `virus_hunter.py`: ele implementa literalmente a combinação `SAVaC` publicada em
> Deng et al. 2015, `firstpage.py` importa dele, e o `virus_hunter.pyc` commitado prova
> execução real quatro dias antes do upload. Ver [ADR-0004](0004-virus-hunter-as-reference.md).
> O texto abaixo fica preservado como registro do estado da questão antes da decisão.

## Contexto

O repositório contém cinco variantes do mesmo orquestrador. Duas são candidatas reais a
referência: `readseeds2.py` (997 linhas) e
[`virus_hunter.py`](../../script/virus_hunter.py) (2.233 linhas).

A comparação completa está em [`docs/orchestrators.md`](../orchestrators.md). O ponto
central: **eles não são o mesmo pipeline com features diferentes — produzem resultados
científicos materialmente distintos.**

- `readseeds2.py` sempre monta contigs; `virus_hunter.py`, no estado commitado, não monta.
- `readseeds2.py` filtra contra NR comparando e-values; `virus_hunter.py` usa lista negra.
- O corte de contig antes do BLAST difere em 5× (300 bp vs 1500 bp).
- Um roda *paired-end*, o outro *single-end*.

Escolher entre eles é escolher **qual comportamento científico será preservado** pela
refatoração. Não é uma decisão de engenharia, e por isso não pode ser tomada por leitura
de código.

## Alternativas consideradas

**`readseeds2.py`.** Sempre monta; usa o filtro NR estatisticamente mais forte; é o único
que roda sem o cluster original (não tem SSH em tempo de import); é o indicado pelo
`script/readme.txt`; foi o alvo do trabalho anterior do grupo em jan/2025. Em contrapartida,
não tem SPAdes, DIAMOND, CLARK nem HMMER, e carrega o defeito da `soap_single()` duplicada.

**`virus_hunter.py`.** Ferramental moderno e muito mais configurável. Em contrapartida,
não monta nada no estado commitado, usa o filtro NR mais fraco (com a rota forte
comentada), traz credenciais em texto claro e `chmod 777`, e o SSH em tempo de import
precisa ser removido antes de qualquer teste local.

**Definir o pipeline alvo explicitamente.** Tratar ambos como legado e escolher o
comportamento etapa por etapa, com decisão registrada. Mais lento, mas evita herdar
parâmetros que ninguém escolheu conscientemente — vários dos valores atuais não têm
justificativa registrada em lugar nenhum.

## Decisão

**Em aberto.** Registrada como pendente para que a ausência de decisão seja explícita, e
para que a evidência já levantada não se perca.

Enquanto pendente, valem duas regras de trabalho:

1. Nenhuma mudança que altere o comportamento científico de qualquer orquestrador.
2. Priorizar trabalho independente desta decisão — documentação, higiene de repositório,
   infraestrutura de validação.

## Evidências que resolveriam a questão

1. A seção de métodos de artigos publicados pelo grupo com este pipeline. **Evidência mais
   forte.**
2. Qualquer `run.log` de execução real preservado — os valores de `n` e `contigLength2`
   identificam o orquestrador sem ambiguidade.
3. Confirmação de se a montagem é obrigatória no protocolo do grupo. Se for, o estado
   commitado de `virus_hunter.py` é um estado de teste, e a comparação muda.
4. Confirmação de se as amostras atuais são *paired-end* ou *single-end*.

## Consequências

- O trabalho segue por frentes independentes desta decisão até que ela seja tomada.
- Quanto mais tarde a decisão, maior o risco de trabalho feito sobre o orquestrador que
  vier a ser descartado. Frentes que dependem desta escolha devem ser adiadas, não
  iniciadas "no mais provável".
- Quando decidida: esta ADR passa a `Substituída por ADR-XXXX`, e a nova registra a
  escolha, a evidência que a sustentou e o destino dos demais orquestradores.

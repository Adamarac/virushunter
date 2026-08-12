# Documentação técnica — VirusHunter

Esta pasta documenta o pipeline **como ele é hoje**, antes de qualquer refatoração.

O código deste repositório foi publicado em julho de 2020 como um upload único, sem
histórico incremental. Não havia documentação de arquitetura, de fluxo de execução ou
dos contratos entre componentes. Estes documentos reconstroem essa informação a partir
da leitura do código, para que a refatoração possa ser feita com segurança.

## Como ler

Comece por [`invariants.md`](invariants.md). Ele descreve três regras não escritas que
sustentam o pipeline inteiro. Quebrá-las não produz erro — produz resultado errado em
silêncio. É o documento mais importante desta pasta.

| Documento | Conteúdo |
|---|---|
| [`invariants.md`](invariants.md) | Regras implícitas que o código depende e não verifica |
| [`pipeline.md`](pipeline.md) | Fluxo real de execução, etapa a etapa |
| [`architecture.md`](architecture.md) | Camadas, componentes e como se acoplam |
| [`orchestrators.md`](orchestrators.md) | Comparação entre os orquestradores concorrentes |
| [`known-issues.md`](known-issues.md) | Problemas identificados, com evidência e impacto |
| [`decisions/`](decisions/) | Registro de decisões de arquitetura (ADR) |

## Convenções destes documentos

Toda afirmação sobre o comportamento do código é acompanhada da evidência
(`arquivo:linha`). Onde não foi possível determinar algo com segurança, o texto marca
explicitamente **"não determinado"** ou **"hipótese"** e diz qual evidência resolveria a
questão. Documentação de pipeline científico que apresenta suposição como fato é pior do
que documentação ausente.

Os documentos distinguem sempre três coisas:

- **o que o código faz** — verificável no fonte;
- **o que parece ter sido planejado** — inferido, e marcado como inferência;
- **o que se recomenda mudar** — proposta, nunca descrição.

## Estado

Estes documentos descrevem o código no estado do commit inicial de 2020 (`543307f`,
`7370d54`). Ainda não houve mudança de comportamento no pipeline.

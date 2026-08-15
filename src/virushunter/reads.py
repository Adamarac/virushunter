# Cada leitura recebe um nome novo baseado na posicao dela no arquivo, e nao no
# nome que veio do sequenciador. O pipeline inteiro depende disso: etapas
# posteriores reencontram uma leitura pela posicao, entao a ordem nunca pode mudar.

LINES_PER_RECORD = 4


def read_ordinal(line_number: int) -> int:
    """Numero da leitura, contando a partir da linha em que ela comeca no arquivo."""
    return line_number // LINES_PER_RECORD


def read_id(line_number: int, pair: str, library: str) -> str:
    """Monta o nome da leitura no formato usado pelo pipeline: @s12_1_amostra."""
    return f"@s{read_ordinal(line_number)}_{pair}_{library}"

#!/usr/bin/env python
# Le o NR e os genomas virais, descobre a que especie cada sequencia pertence e
# separa em arquivos por tipo (viral, fago, nao-viral), escrevendo a taxonomia no
# proprio cabecalho. O pipeline depende desse cabecalho: build_report.py tira dele
# especie, genero e familia, e filter_nr.py decide o descarte pelo prefixo.
#
# Migrado de nr_virus3.py (Python 2); o que mudou esta na ADR-0022.

import argparse
import gzip
import os

nodes = {}
names = {}
name2tid = {}
acc2tid = {}

giset = set([])
c1, c2, ap, h, v, nv, p, hm = 0, 0, 0, 0, 0, 0, 0, 0
cats = set([])

# Nomes que aparecem milhares de vezes no NR; so a primeira ocorrencia de cada um
# entra no banco, para nao inflar o resultado com um unico virus.
REPETIDOS = ['Human immunodeficiency virus 1', 'Hepatitis C virus',
             'Influenza A virus', 'Hepatitis B virus']


class Node(object):
    """Um no da arvore taxonomica, que sabe subir ate a raiz."""

    def __init__(self, tid, level=None):
        self.tid = tid
        self.parent = None
        self.children = []
        self.level = level

    def add_parent(self, parent):
        self.parent = parent
        parent.children.append(self)

    def get_fullpath(self):
        rval = [self.tid]
        node = self
        while node.parent is not None:
            tmp = node.parent
            rval.append(tmp.tid)
            node = tmp
        return rval

    def printTree(self, depth, of):
        for child in self.children:
            level = child.level
            if level == 'no rank':
                level = ''
            try:
                nm = names[child.tid].replace(' ', '_')
            except:
                nm = 'none'
            # O print do Python 2 nao punha espaco depois de uma tabulacao; o do
            # Python 3 poe sempre. Montado a mao para a saida sair igual.
            recuo = "\t" * depth
            resto = ' '.join(['-', str(depth), level, nm])
            print(recuo + ('' if recuo else ' ') + resto, file=of)
            child.printTree(depth + 1, of)


def classifica(line, isnr, filter2):
    """Descobre a linhagem de uma sequencia e devolve os rotulos e o que ela e."""
    global c1, ap
    resultado = {'human': False, 'phage': False, 'herv': False, 'virus': False,
                 'appeared': False, 'nolabel': False, 'label': [], 'acc': None}

    acc = line.strip().split()[0][1:]
    resultado['acc'] = acc
    if 'HUMAN' in line.upper() or 'SAPIENS' in line.upper():
        resultado['human'] = True
    if not isnr:
        giset.add(acc)
    else:
        for key in REPETIDOS:
            if key.upper() in line.upper():
                filter2[key.upper()] += 1
                if filter2[key.upper()] > 1:
                    ap += 1
                    resultado['appeared'] = True
                    break
        if acc in giset:
            ap += 1
            resultado['appeared'] = True
    if resultado['appeared']:
        return resultado

    taxname = line[(line.find('[') + 1):(line.find(']'))]
    if taxname in name2tid:
        taxid = name2tid[taxname]
        c1 += 1
    elif acc in acc2tid:
        taxid = acc2tid[acc]
        c1 += 1
    else:
        resultado['nolabel'] = True
        taxid = '0'

    try:
        path = nodes[taxid].get_fullpath()
    except:
        path = []
    if path == []:
        resultado['nolabel'] = True
    if resultado['nolabel']:
        return resultado

    k = 0
    category, family, genus, species = 'None', 'None', 'None', 'None'
    for tid in path:
        k += 1
        try:
            level = nodes[tid].level.replace(' ', '_')
        except:
            level = 'None'
        try:
            nm = names[tid].replace(' ', '_')
        except:
            nm = 'None'

        if level == 'species':
            species = nm
        elif level == 'genus':
            genus = nm
        elif level == 'family':
            family = nm
        elif level == 'no_rank' and k == (len(path) - 2):
            category = nm
        elif level == 'superkingdom' and nm == 'Viruses':
            resultado['virus'] = True
        if 'PHAGE' in nm.upper():
            resultado['phage'] = True
        if 'HUMAN_ENDOGENOUS_RETROVIRUSES' == nm.upper():
            resultado['herv'] = True
    if resultado['herv']:
        category = 'HERV'
    if resultado['phage']:
        category = 'Phage'
    resultado['label'] = ['species' + '$' + species, 'genus' + '$' + genus,
                          'family' + '$' + family, 'category' + '$' + category]
    cats.add(category)
    return resultado


def acessos_citados(arquivos):
    """Quais accessions vao precisar do mapa: os cujo [organismo] nao resolve pelo nome."""
    necessarios = set()
    for infile in arquivos:
        if not os.path.exists(infile):
            continue
        with gzip.open(infile, 'rt') as f:
            for line in f:
                if not line.strip().startswith('>'):
                    continue
                acc = line.strip().split()[0][1:]
                taxname = line[(line.find('[') + 1):(line.find(']'))]
                if taxname not in name2tid:
                    necessarios.add(acc)
    return necessarios


def loadTax(necessarios=None, escrever_arvore=True):
    """Monta a arvore taxonomica e o mapa de accession para especie."""
    f = open('nodes.dmp', 'r')
    for line in f:
        parts = line.strip().split('|')
        tid, pid, level = parts[0].strip(), parts[1].strip(), parts[2].strip()
        nodes[tid] = Node(tid, level)
    f.close()

    f = open('nodes.dmp', 'r')
    for line in f:
        parts = line.strip().split('|')
        tid, pid, level = parts[0].strip(), parts[1].strip(), parts[2].strip()
        n1 = nodes[tid]
        if tid != pid:
            n2 = nodes[pid]
            n1.add_parent(n2)
    f.close()

    f = open('names.dmp', 'r')
    for line in f:
        if 'scientific name' in line:
            parts = line.strip().split('|')
            tid = parts[0].strip()
            name = parts[1].strip()
            name2tid[name] = tid
            # ':' e '$' estruturam o cabecalho; um nome que os contenha quebraria
            # a leitura feita adiante pelo build_report.
            names[tid] = name.replace(':', '_').replace('$', '_')
    f.close()

    if escrever_arvore:
        of = open('tax_tree.txt', 'w')
        nodes['1'].printTree(0, of)
        of.close()

    for mapa in ('prot.accession2taxid.gz', 'nucl_gb.accession2taxid.gz'):
        if not os.path.exists(mapa):
            print('mapa ausente, ignorado:', mapa)
            continue
        f = gzip.open(mapa, 'rt')
        f.readline()  # cabecalho
        for line in f:
            parts = line.strip().split()
            if necessarios is None or parts[1] in necessarios:
                acc2tid[parts[1]] = parts[2]
        f.close()
    print('accessions no mapa', len(acc2tid))


def addTaxon(infile, isnr):
    """Separa as proteinas em viral, fago, humano-viral e o banco unico do DIAMOND."""
    global c2, h, v, nv, p, hm
    print('isnr', isnr, 'giset size', len(giset))
    filter2 = {k.upper(): 0 for k in REPETIDOS}
    f = gzip.open(infile, 'rt')

    modo = 'a' if isnr else 'w'
    hf = open('human.virome.fa', modo)
    virusf = open('virus.tmp.fa', modo)
    phagef = open('phage.fa', modo)
    df = open('diamond.fa', modo)

    r = {'human': False, 'phage': False, 'herv': False, 'virus': False,
         'appeared': False, 'nolabel': False}
    total = 0
    for line in f:
        if line.strip().startswith('>'):
            total += 1
            if total % 100000 == 0:
                print('total fa sequence', total)
            r = classifica(line, isnr, filter2)
            if r['appeared'] or r['nolabel']:
                continue
            acc = '>' + r['acc']
            rotulo = ':'.join(r['label'])
            if r['human'] and r['virus']:
                hm += 1
                print(acc + ' ' + rotulo, file=hf)
            if r['herv']:
                h += 1
                continue
            elif r['phage']:
                diamondLabel = 'PHAGE'
                p += 1
                print(acc + ' ' + rotulo, file=phagef)
            elif r['virus']:
                diamondLabel = 'VIRUS'
                v += 1
                print(acc + ' ' + rotulo, file=virusf)
            else:
                nv += 1
                diamondLabel = 'NV'
            print('>' + diamondLabel + '_' + str(total) + '_' + rotulo, file=df)
        else:  # linha de sequencia
            if r['appeared'] or r['nolabel']:
                continue
            if r['human'] and r['virus']:
                print(line.strip().replace('-', ''), file=hf)
            if r['herv']:
                continue
            elif r['phage']:
                print(line.strip(), file=phagef)
            elif r['virus']:
                print(line.strip().replace('-', ''), file=virusf)
            print(line.strip().replace('-', ''), file=df)

    print(cats)
    c2 = total - c1
    print('duplicated', ap, 'with taxon', c1, 'without taxon', c2, 'virus', v,
          'non-virus', nv, 'herv', h, 'phage', p, 'human', hm)
    print(filter2)
    for handle in (hf, virusf, phagef, df):
        handle.close()
    f.close()


def addLinlinHerv():
    """Junta os retrovirus endogenos humanos ao banco viral, rotulados como HERV."""
    f = open('virus.tmp.fa', 'r')
    f2 = open('HERVaa.fasta', 'r')
    of = open('virus.fa', 'w')
    for line in f:
        of.write(line)
    for line in f2:
        if line.strip() == '':
            continue
        elif line.strip().startswith('>'):
            if line.strip()[1:].strip().startswith('gi|'):
                species = '_'.join(line.strip()[1:].split()[1:])
            else:
                species = '_'.join(line.strip()[1:].strip().split())
            of.write(line.strip() + ' species$' + species +
                     ':genus$HERV:family$HERV:category$HERV\n')
        else:
            of.write(line)
    f.close()
    f2.close()
    of.close()


def addTaxonDNA(infile, isnr):
    """Mesma classificacao, para os genomas em DNA; escreve so o banco viral."""
    global c2, h, v, nv, p
    print('isnr', isnr, 'giset size', len(giset))
    filter2 = {k.upper(): 0 for k in REPETIDOS}
    f = gzip.open(infile, 'rt')
    virusf = open('virus.DNA.fa', 'a' if isnr else 'w')

    r = {'phage': False, 'herv': False, 'virus': False,
         'appeared': False, 'nolabel': False}
    total = 0
    for line in f:
        if line.strip().startswith('>'):
            total += 1
            if total % 100000 == 0:
                print('total fa sequence', total)
            r = classifica(line, isnr, filter2)
            if r['appeared'] or r['nolabel']:
                continue
            if r['herv']:
                h += 1
                continue
            elif r['phage']:
                p += 1
            elif r['virus']:
                v += 1
                print('>' + r['acc'] + ' ' + ':'.join(r['label']), file=virusf)
            else:
                nv += 1
        else:
            if r['appeared'] or r['nolabel']:
                continue
            if r['herv'] or r['phage']:
                continue
            elif r['virus']:
                print(line.strip().replace('-', ''), file=virusf)

    print(cats)
    c2 = total - c1
    print('duplicated', ap, 'with taxon', c1, 'without taxon', c2, 'virus', v,
          'non-virus', nv, 'herv', h, 'phage', p, 'human', hm)
    print(filter2)
    virusf.close()
    f.close()


def main():
    argumentos = argparse.ArgumentParser(
        description='Separa NR e genomas virais por taxonomia, gravando-a no cabecalho.')
    argumentos.add_argument('etapa', choices=['proteins', 'dna'],
                            help='proteins: virus.fa, phage.fa e diamond.fa; dna: virus.DNA.fa')
    argumentos.add_argument('--mapa-inteiro', action='store_true',
                            help='carrega todo o accession2taxid na memoria, como o original')
    args = argumentos.parse_args()

    print('current directory', os.getcwd())
    entradas = (['viral.protein.fa.gz', 'nr.gz'] if args.etapa == 'proteins'
                else ['viral.genomic.fa.gz'])

    print('loading taxons')
    if args.mapa_inteiro:
        loadTax(None)
    else:
        # O mapa tem mais de um bilhao de accessions; guardar tudo custaria centenas
        # de GB. Primeiro descobrimos quais serao consultados, depois lemos so esses.
        loadTax(set(), escrever_arvore=True)
        necessarios = acessos_citados(entradas)
        print('accessions a buscar no mapa', len(necessarios))
        loadTax(necessarios, escrever_arvore=False)

    if args.etapa == 'proteins':
        print('adding taxons virus')
        addTaxon('viral.protein.fa.gz', False)
        print('adding taxons nr')
        addTaxon('nr.gz', True)
        addLinlinHerv()
    else:
        addTaxonDNA('viral.genomic.fa.gz', False)


if __name__ == '__main__':
    main()

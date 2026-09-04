#!/usr/bin/env python
# Descarta candidatos virais que se parecem mais com algo nao viral.
# Dois metodos, escolhidos em steps.nr_filter_method: "diamond" olha so quem foi
# o parente mais proximo; "blast" compara o quanto cada semelhanca foi boa.
import linecache
import re
import sys

from Bio.Blast import NCBIXML

from virushunter.config import load as load_config
from virushunter.fasta import index_headers, sequence


def readVirusGI():
    """Os identificadores do banco viral, para nao usar um hit viral contra si mesmo."""
    f = open(load_config()['databases.virus_fasta'])
    virusGIs = []
    for line in f:
        if line.strip().startswith('>'):
            try:
                virusGIs.append('GI|' + line.strip().split('|')[1] + '|')
            except Exception:
                pass
    f.close()
    return set(virusGIs)


def readNRXML(fname, virusGIs):
    """Metodo blast: melhor e-value nao viral de cada candidato, lido do XML."""
    result_handle = open(fname)
    nrE, nrID = {}, {}
    for blast_record in NCBIXML.parse(result_handle):
        query = blast_record.query
        for alignment in blast_record.alignments:
            subject = alignment.title.upper()
            if any(m in virusGIs for m in re.findall(r'GI\|\d+\|', subject)):
                continue
            if ('VIRUS' in subject) or ('VIRAL' in subject):
                continue
            for hsp in alignment.hsps:
                if query not in nrE or float(hsp.expect) < float(nrE[query]):
                    nrE[query] = float(hsp.expect)
                    nrID[query] = subject
    result_handle.close()
    return nrE, nrID


def readDiamondNR(fname):
    """Metodo diamond: lista negra com quem teve parente mais proximo nao viral."""
    f = open(fname)
    nrE = set([])
    for line in f:
        parts = line.strip().split()
        query, subject = parts[0], parts[1]
        if subject.strip().split('_', 1)[0] != "VIRUS":
            nrE.add(query)
    f.close()
    return nrE


def readVirusXML1(fname, metodo):
    """Melhor e-value viral de cada candidato; no metodo diamond, erro de XML e ignorado."""
    result_handle = open(fname)
    virusE, virusID = {}, {}
    try:
        for blast_record in NCBIXML.parse(result_handle):
            query = blast_record.query
            for alignment in blast_record.alignments:
                subject = alignment.title.upper()
                for hsp in alignment.hsps:
                    if query not in virusE or float(hsp.expect) < virusE[query]:
                        virusE[query] = float(hsp.expect)
                        virusID[query] = subject
    except Exception:
        if metodo != 'diamond':
            raise
    result_handle.close()
    return virusE, virusID


def descartar(query, expect, metodo, nrE, virusE):
    """A regra que separa os dois metodos: pertencer a lista negra ou perder no e-value."""
    if metodo == 'diamond':
        return query in nrE
    return query in nrE and query in virusE and expect >= nrE[query]


def OutputVirus(fname, filtertxt, hsp_only, E_VALUE_THRESH, metodo, nrE, virusE,
                cache, cachename):
    """Escreve o bloco de 11 linhas de cada hit que sobreviveu ao filtro."""
    of = open(filtertxt, 'w')
    result_handle = open(fname)
    nalign, filtrados = 0, 0
    try:
        for blast_record in NCBIXML.parse(result_handle):
            query = blast_record.query
            for alignment in blast_record.alignments:
                for hsp in alignment.hsps:
                    if float(hsp.expect) >= E_VALUE_THRESH:
                        continue
                    if descartar(query, float(hsp.expect), metodo, nrE, virusE):
                        filtrados += 1
                        continue
                    nalign += 1
                    query_nt = sequence(cachename, cache, blast_record.query)
                    if hsp_only == 'YES':
                        query_nt = query_nt[int(hsp.query_start) - 1:int(hsp.query_end)]
                    # O metodo diamond nao guarda o e-value nao viral, so a lista negra.
                    nre = '-' if metodo == 'diamond' else nrE.get(query, 'no-hit')
                    of.write('****Alignment****\n')
                    of.write(blast_record.query + '\n')
                    of.write('query_nt ' + query_nt + '\n')
                    of.write('subject: ' + alignment.title + '\n')
                    of.write('length: ' + str(alignment.length) + '\n')
                    of.write('e value: ' + str(hsp.expect) + '\n')
                    of.write('lowest non-virus nr e value (LNVNRE) ' + str(nre) + '\n')
                    of.write('identities: ' + str(hsp.identities) + '\n')
                    of.write(str(hsp.query_start).ljust(11) + ' ' + hsp.query + '\n')
                    of.write(' '.ljust(11) + ' ' + hsp.match + '\n')
                    of.write(str(hsp.sbjct_start).ljust(11) + ' ' + hsp.sbjct + '\n')
    except Exception:
        if metodo != 'diamond':
            raise
        print('XML format bad')
    result_handle.close()
    of.close()
    print(fname, ' n_hits = ', str(nalign))


if __name__ == '__main__':
    virusxml = sys.argv[1]
    nrfile = sys.argv[2]
    cachename = sys.argv[3]
    filtertxt = sys.argv[4]
    # Converte para numero. Sem isso a comparacao adiante da sempre certo e o
    # limite de e-value configurado nao vale para nada.
    E_VALUE_THRESH = float(sys.argv[5])
    try:
        hsp_only = sys.argv[6]
    except IndexError:
        hsp_only = 'NO'
    try:
        metodo = sys.argv[7]
    except IndexError:
        metodo = 'diamond'
    if metodo not in ('diamond', 'blast'):
        sys.exit(f'metodo invalido: {metodo!r}; use "diamond" ou "blast"')
    print('hsp_only', hsp_only)

    cache = index_headers(cachename)
    virusE, virusID = readVirusXML1(virusxml, metodo)
    if metodo == 'diamond':
        try:
            nrE = readDiamondNR(nrfile)
        except Exception:
            nrE = set([])
            print('no diamond')
    else:
        try:
            nrE, nrID = readNRXML(nrfile, readVirusGI())
        except Exception:
            nrE = {}
    OutputVirus(virusxml, filtertxt, hsp_only, E_VALUE_THRESH, metodo, nrE, virusE,
                cache, cachename)

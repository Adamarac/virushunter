#!/usr/bin/env python
# Conta quantas leituras de uma amostra alinharam em cada contig.

import sys
from collections import defaultdict


def identity(MD):
	MD=MD.replace('A', ' ').replace('C', ' ').replace('G', ' ').replace('T', ' ').replace('^', ' ').replace('N', ' ')
	mismatch=MD.count(' ')
	ps=MD.split()
	match=sum([int(x) for x in ps])
	if match<50: return 0.0
	return float(match)/(mismatch+match)

def processPairedSAM(filename, countfile):
	if filename[-3:]==".gz":
		import gzip
		f=gzip.open(filename, 'rt')
	else: f=open(filename, 'r')
	of=open(countfile, 'w')
	counts=defaultdict(int)
	appeared=set([])
	cc=defaultdict(list)
	total, totalPair, mapped=0,0,0 #total hits paired count as 1, total paired hits
	for line in f:
		parts=line.strip().split('\t')
		(name, flag, chro, start, mapq, cigar)=parts[0:6]
		if parts[-3].startswith('MD'):
			MD=parts[-3].split(':')[-1]
		elif parts[-2].startswith('MD'):
			MD=parts[-2].split(':')[-1]
		else: continue
		if chro =='*' or cigar=='*':
			continue
		if identity(MD)<0.95: continue
		mapped+=1
		cc[name].append(line)
		if name in appeared:
			totalPair+=1
			continue
		appeared.add(name)
		counts[chro]+=1
		total+=1
	f.close()
	print('total hits (paired count as 1)=', total,  'total paired hits =',totalPair, 'mapped=', mapped)
	for chro, count in list(counts.items()):
		of.write(chro+'\t'+str(count)+'\n')
	of.close()

if __name__ == "__main__":
	processPairedSAM(sys.argv[1], sys.argv[2]) #pair end sam file


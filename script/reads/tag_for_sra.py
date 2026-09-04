#!/usr/bin/env python
# Reetiqueta os cabecalhos das leituras no formato que a submissao ao SRA espera,
# acrescentando tudo a um unico arquivo.
import sys, gzip
infile = sys.argv[1]
if infile.endswith('.gz'):
	f=gzip.open(sys.argv[1], 'rt')
else:
	f=open(sys.argv[1], 'r')
of=gzip.open(sys.argv[3],'at')
id=sys.argv[2]

i=0
for line in f:
	i+=1
	if line.strip()=='': continue
	if i%4==1:
		of.write(line.strip().split()[0]+' '+id+'\n')
	else:
		of.write(line.strip()+'\n')
if i%4!=0:
	print('invalid fastq', i%4, infile)
f.close()
of.close()

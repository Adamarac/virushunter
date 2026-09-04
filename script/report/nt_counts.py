#!/usr/bin/env python
# Conta leituras por taxon a partir dos SAM da busca contra o banco nt.

import sys
import os
import os.path
from collections import defaultdict
from operator import itemgetter
import linecache
import os.path
from virushunter.fasta import index_headers, sequence



def processSAM(key, wd, base, startInd, endInd, cache): # first scan to get the mutation positions
	countfile=wd+'/'+base+'/clark/'+key+'.count'
	of=open(countfile,'w')
	of2=open(countfile+'.csv','w')

	fs1=[]
	for j in range(startInd, endInd+1):
		filename=wd+'/NT/'+ key+'_'+str(j)+'.sam'
		fs1.append(open(filename, 'r'))

	count1=defaultdict(int)
	counts2=defaultdict(list)

	while 1:
		# Todos os SAM avancam juntos: eles descrevem a MESMA leitura em cada
		# posicao, entao parar num acerto deixaria os demais para tras e, dali em
		# diante, leituras diferentes seriam comparadas entre si (K2).
		linhas = [f1.readline() for f1 in fs1]
		if not all(linhas):
			if any(linhas):
				sys.exit('SAM com numero de linhas diferente na amostra ' + key)
			break
		hit = False
		for line1 in linhas:
			parts=line1.strip().split('	')
			name, chro, seq=parts[0], parts[2], parts[9]
			if chro !='*' and len(seq)>20:
				chro=chro.replace(',','')
				cat, clas, fam, species=chro.split('$')
				count1[cat]+=1
				category2=chro.replace('$', ',')
				counts2[category2].append(name)
				hit=True
				break
		if not hit:
			count1['NA']+=1

		# (name, flag, chro, sstart, mapq, cigar)=parts[0:6]
	for f1 in fs1:
		f1.close()

	for key in list(count1.keys()):
		of.write(key+'\t'+str(int(count1[key]))+'\n')
	of.close()

	of2.write('category,class,family,species,count\n')

	x=[(key, len(snames)) for (key, snames) in list(counts2.items())]
	sorted_x = sorted(x, key=itemgetter(1), reverse=True)

	for key, val in sorted_x:
		seqnames=counts2[key]
		of2.write(key+','+str(int(val))+'\n')
		key2=key.replace(',', '_').replace('/', '_')
		outfa=wd+'/'+base+'/clark/fasta/'+os.path.basename(countfile)+'.csv.'+key2+'.fa'
		fa=open(outfa, 'w')
		for seqname in seqnames:
			query_nt = sequence(fafile, cache, seqname)
			fa.write('>'+seqname+'\n')
			fa.write(query_nt+'\n')
		fa.close()

	of2.close()

if __name__ == "__main__":
	key=sys.argv[1]
	wd=sys.argv[2]
	base=sys.argv[3]
	startInd=int(sys.argv[4])
	endInd=int(sys.argv[5])
	
	fafile=wd+'/fastq/'+key+'.fa'
	cache = index_headers(fafile)
	processSAM(key, wd, base, startInd, endInd, cache)

#!/usr/bin/env python
# Conta quantas leituras cairam em cada especie, a partir da saida do CLARK.
import sys
from collections import defaultdict
import os
import operator
import linecache
import os.path
from virushunter.fasta import index_headers, sequence

def plotpie(countfile):
	Rfile=countfile+'.R'
	of3 = open(Rfile, 'w')
	pieout=countfile+'.png'
	
	Rscript = "x=as.factor(c('Viridiplantae', 'NA', 'Fungi', 'Metazoa','Viruses', 'Phage', 'Archaea', 'Bacteria'))\n" +\
			"y=as.factor(  c('lightgreen',  'white','gray',  'blue',   'yellow',  'orange','pink'   ,'brown'))\n" +\
			' a<-read.table("'+countfile+'", header=F,  stringsAsFactors=F)\n'+ \
			'family <- as.numeric(a[[2]])\n'+\
			'lab<-a[[1]]\n'+\
			"lab[is.na(lab)]<-'NA'\n" +\
			'png("'+pieout+'", res=150, width=1000, height=1000)\n' +\
			'pie(family , col=as.character(droplevels(y[match(lab, x)])), labels=lab)\n'+\
			'dev.off()\n'
	of3.write(Rscript)
	of3.close()
	cmd='R CMD BATCH --quiet --vanilla '+Rfile
	print(cmd)
	os.system(cmd)

indexf=open(sys.argv[1], 'r')
f1=open(sys.argv[2], 'r')
countfile=sys.argv[3]
fafile=sys.argv[4]
path=sys.argv[5]
of=open(countfile,'w')
of2=open(countfile+'.csv','w')
#of2=open(fafile,'r')
cache = index_headers(fafile)

index={}
for line in indexf:
	ind, species = line.strip().split()
	index[ind]=species
indexf.close()
index['NA']='NA_NA_NA'

# header=f1.readline()
# header=f2.readline()
# header=f3.readline()
counts=defaultdict(int)
counts2=defaultdict(list)
for line in f1:
	if line.startswith('Object_'): continue
	parts=line.strip().split(',')
	seqname=parts[0]
	categoryind=parts[-1]
	category=index[categoryind]
	cat, clas, fam = category.split('_', 2)
	counts[cat]+=1
	category2=','.join([cat, clas, fam])
	counts2[category2].append(seqname)
# for line in f2:
	# category=line.strip().split(',')[-1]
	# counts[category]+=1
# for line in f3:
	# category=line.strip().split(',')[-1]
	# counts[category]+=1
for key in list(counts.keys()):
	of.write(key+'\t'+str(int(counts[key]/3))+'\n')
of2.write('category,class,family,count\n')

x=[(key, len(snames)) for (key, snames) in list(counts2.items())]
sorted_x = sorted(x, key=operator.itemgetter(1), reverse=True)

for key, val in sorted_x:
	seqnames=counts2[key]
	of2.write(key+','+str(int(val//3)+1)+'\n')
	key2=key.replace(',', '_')
	outfa=path+'/clark/fasta/'+os.path.basename(countfile)+'.csv.'+key2+'.fa'
	fa=open(outfa, 'w')
	for seqname in seqnames:
		query_nt = sequence(fafile, cache, seqname)
		fa.write('>'+seqname+'\n')
		fa.write(query_nt+'\n')
	fa.close()
# /mnt/cluster2/Vhunt/170901_EA_TIMMS_HIV_HCV/clark_out/W200315513079.csvv
f1.close()
# f2.close()
# f3.close()
of.close()
of2.close()
plotpie(countfile)
#!/usr/bin/env python

from Bio.Blast import NCBIXML
import sys
import linecache
import fcntl
from virushunter.fasta import index_headers, sequence

def print_mysterious(cachename, cache, queryset, outfile, length):
	nmys=0
	of=open(outfile, 'w')
	for header in list(cache.keys()):
		if header in queryset: #hits
			continue
		seq=sequence(cachename, cache, header)
		if len(seq)> length:
			nmys+=1
			of.write('>'+header+'\n')
			of.write(seq+'\n')
	of.close()
	return nmys #number of mysterious contigs

if __name__ == '__main__': 
	fname=sys.argv[1]
	cachename = sys.argv[2]
	fsigname=sys.argv[3]
	mysfile=sys.argv[4]
	myslen=int(sys.argv[5])
	e_threshold=float(sys.argv[6])
	logfile=sys.argv[7]
	cache={}
	cache = index_headers(cachename)
	result_handle = open(fname, 'r')
	
	queryset=set()
	sigReads=0
	f = open(fsigname, 'w')	
	
	try: 
		blast_records = NCBIXML.parse(result_handle)
		for blast_record in blast_records:
			for alignment in blast_record.alignments:
				for hsp in alignment.hsps:
					if hsp.expect < e_threshold:
						query_nt = sequence(cachename, cache, blast_record.query)
						if blast_record.query not in queryset:
							if True:#(hsp.expect > 10E-15) :
								f.write('>'+blast_record.query+'\n')
								f.write(query_nt+'\n')
							sigReads+=1
						queryset.add(blast_record.query)
	except:
		print('bad xml', fsigname)
		pass
	result_handle.close()
	f.close()
	nmys=print_mysterious(cachename, cache, queryset, mysfile, myslen)
	f10=open(logfile, 'a')
	fcntl.flock(f10, fcntl.LOCK_EX)
	f10.write(fname+' Sig_Vreads ='+' '+str(sigReads)+'\n')
	fcntl.flock(f10, fcntl.LOCK_UN)
	f10.close()
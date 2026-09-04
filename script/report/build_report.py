#!/usr/bin/env python

from collections import defaultdict
import sys
import os
import os.path
import linecache
def outputHeader(of):
	head ='''
<html>
<head>
<link rel="stylesheet" type="text/css" href="../tablestyle.css">
</head>
<script src="../sorttable.js">
</script>
<script src="../ajax_select.js">
</script>
E-value output range: from <input type="text" id="evalue1" name="evalue1" value="0"> to <input type="text" id="evalue2" name="evalue2" value="1"><br>
<button type="button" onclick="update_Evalue_range()">Update Table </button><br>
<br>
<input type="checkbox" name='checkall' value='checkall' onclick="checkAll(this)">
Check All <button onclick="exportData()" >Export Selected</button> <br>

 <div id="txtHint"> </div>

'''


	of.write(head+'\n')

	
def hitHeader(of):
	head ='''
	<html>
	<head>
		<style type="text/css" title="currentStyle">
			@import "../../DataTables-1.9.4/media/css/demo_page.css";
			@import "../../DataTables-1.9.4/media/css/demo_table.css";
		</style>
		<script type="text/javascript" language="javascript" src="../../DataTables-1.9.4/media/js/jquery.js"></script>
		<script type="text/javascript" language="javascript" src="../../DataTables-1.9.4/media/js/jquery.dataTables.js"></script>
		<script type="text/javascript" charset="utf-8">
			$(document).ready( function() {
			$('#example').dataTable( {
			"iDisplayLength": 500,
			"sPaginationType": "full_numbers"
		} );
} )
		</script>
	</head>
	<table cellpadding="0" cellspacing="0" border="0" class="display" id="example">
	<thead><tr><th>Virus</th><th>Query</th><th>Pair Hit</th><th>Evalue</th><th>LNVNRE</th><th>Identity</th><th>Alignment</th><th>Query_nt</th><th>Pair_nt</th></tr></thead><tbody>
'''
	
	of.write(head+'\n')

def CacheFASTA(fname, hit_pairs):
	cachecombine={}
	f = open(fname, 'r')
	i=0
	start, end = 0,0
	header= None
	print('caching fasta')
	for line in f:
		i+=1
		if i%10000000==0: print('caching fasta line', i)
		if line.strip().startswith('>'):
			end=i-1
			if header!=None and (header in hit_pairs): 
				cachecombine[header] = (start, end)
			line=line[1:]
			if line.startswith('@'):
				parts = line.strip().split('_')
				header= parts[0]+'_'+parts[1]
			else: header=''
			start=i+1
	if header!=None and (header in hit_pairs): cachecombine[header] = (start, i)
	print('cacheFASTA done')
	return cachecombine

def getPairSeq(header, combine, cachecombine):
	seq=[]
	try: start, end = cachecombine[header]
	except: return ''
	for i in range(start, end+1):
		seq.append(linecache.getline(combine, i).strip())
	return ''.join(seq)

def CacheLines(input): 
	cache=defaultdict(list)
	c2, c5, c10 = defaultdict(int), defaultdict(int), defaultdict(int)
	VE={}
	NE={}
	tax={}
	qlen={}
	hit_pairs=set([])
	f = open(input, 'r')
	i=0
	for line in f:
		i+=1
		if i%11 == 2 and line.startswith('@'):
			parts=line.strip().split('_')
			if parts[1]=='1': hit_pairs.add(parts[0]+'_'+'2')
			elif parts[1]=='2': hit_pairs.add(parts[0]+'_'+'1')
		if i%11 == 3:
			try: query = line.strip().split()[1]
			except: 
				print(i, line)
				sys.exit(1)
		if i%11 == 4:
			taxonomy=line.strip().split()[-1]
			try: virus=taxonomy.split(':')[0].split('$')[1]
			except: print(i, line); sys.exit()
			cache[virus].append(i-3)
			tax[virus]=taxonomy
			if virus not in qlen:
				qlen[virus]=len(query)
			elif virus in qlen and qlen[virus]<len(query):
				qlen[virus]=len(query)
		elif i%11==6:
			ve=float(line.split()[-1])
			if ve<=1E-2: 
				c2[virus]+=1
			if ve<=1E-5: 
				c5[virus]+=1
			if ve<=1E-10: 
				c10[virus]+=1
			if virus in VE and ve<VE[virus]:
				VE[virus]=ve
			elif virus not in VE:
				VE[virus]=ve
		elif i%11==7:
			ne=line.split()[-1]
			try: ne=float(ne)
			except: ne=1
			if virus in NE and ne<NE[virus]:
				NE[virus]=ne
			elif virus not in NE:
				NE[virus]=ne
	f.close()
	return cache, VE, NE, tax, qlen, c2, c5, c10, hit_pairs

def printVirusSummary(cache, VE, NE, tax, input, qlen, c2, c5, c10, vcounts, barcodes):
	try: os.mkdir(os.path.dirname(input)+'/pie/')
	except: pass
	try: os.mkdir(os.path.dirname(input)+'/table/')
	except: pass
	base=os.path.basename(input)
	of2 = open(os.path.dirname(input)+'/pie/'+base, 'w')
	of3 = open(os.path.dirname(input)+'/table/'+base, 'w')
	of = open(os.path.splitext(input)[0]+'.html', 'w')
	f4=os.path.splitext(input)[0]+'.xls'
	ff4 = os.path.basename(f4)

	keys=sorted(cache.keys())
	outputHeader(of)
	of.write('<a href=\"'+ff4+'\">excel_download</a>\n')
	of.write('<a href=\"hitTable_e-2.xls\">Table_Evalue10-2</a>\n')
	of.write('<a href=\"hitTable_e-5.xls\">Table_Evalue10-5</a>\n')
	of.write('<a href=\"hitTable_e-10.xls\">Table_Evalue10-10</a>\n')
	of.write('<table class="sortable">\n')
	of.write('<tr><th class="sorttable_nosort"></th><th>Category</th><th>Family</th><th>Genus</th><th>Species</th><th class="sorttable_numeric">Max_Contig</th><th class="sorttable_numeric">Low_V_Evalue</th><th class="sorttable_numeric">Low_NR_Evalue</th><th class="sorttable_numeric">Hits</th><th>fasta</th>')
	for barcode in barcodes:
		of.write('<th>'+barcode+'</th>')
	of.write('</tr>\n')

	numvirus=0
	pie=defaultdict(int)
	for virus in keys:
		try: 
			species, genus, family, cat = tax[virus].split(':')[0:4]
			cat=cat.split('$')[1]
			family=family.split('$')[1]
			genus=genus.split('$')[1]
			species=species.split('$')[1]
		except: cat,species, genus, family = 'NA', 'NA', 'NA', 'NA'
		base=os.path.basename(input)
		virname=''
		for e in species:
			if e.isalnum(): virname+=e
			else: virname+='_'
		label = base+'_'+virname
		f1 = 'aln/'+label+'.html'
		f2 = 'fasta/'+label+'.fa'
		of.write('<tr><td><input type="checkbox" value="'+label+'"> </td>')
		of.write('<td>'+cat+'</td><td>'+family+'</td><td>'+genus+'</td><td>'+species+'</td><td>'+str(qlen[virus])+'</td><td>'+str(VE[virus])+'</td><td>'+str(NE[virus]))
		of.write('</td><td><div id=\"'+label+'_hit\"><a href=\"'+f1+'\">'+str(len(cache[virus]))+'</a></div></td><td>')
		of.write('<div id=\"'+label+'_fa\"><a href=\"'+f2+'\">fasta</a></div></td>')
		
		
		for barcode in barcodes:
			try: vc=vcounts[virname][barcode]
			except: vc=0
			of.write('<td>'+str(vc)+'</td>')
		of.write('</tr>\n')
		of3.write(cat+'\t'+family+'\t'+genus+'\t'+species+'\t'+str(c2[virus])+'\t'+str(c5[virus])+'\t'+str(c10[virus])+'\n')
		pie[family]+=len(cache[virus])
		numvirus+=1
	of.write('</tbody></table></html>\n')
	of.close()
	os.system('cp ' +os.path.splitext(input)[0]+'.html '+f4)
	for (family, count) in list(pie.items()):
		of2.write(family+' '+str(count)+'\n')
	of2.close()
	of3.close()
	print(input, 'num_virus =', numvirus)


	


def detectPair(cache, input):
	keys=sorted(cache.keys())
	allpairs={}
	vv=0
	for virus in keys:
		vv+=1
		allpairs[virus]=defaultdict(set)
		for index in cache[virus]:
			i=1
			id=linecache.getline(input, index+i).strip()
			if id.startswith('@'):
				position, pair = id.split('_')[0:2]
				allpairs[virus][position].add(pair)
	return allpairs

def OutputVirus(cache, input, allpairs, combine, cachecombine, base, cwd):
	keys=sorted(cache.keys())
	try: os.mkdir(os.path.dirname(input)+'/aln/')
	except: pass
	try: os.mkdir(os.path.dirname(input)+'/fasta/')
	except: pass
	countfile=os.path.dirname(input)+'/aln/viralcounts.txt'
	fc=open(countfile, 'w')
	fc.close()
	try: os.mkdir(os.path.dirname(input)+'/tmp/')
	except: pass
	counter=0
	for virus in keys:
		try: 
			species, genus, family, cat = tax[virus].split(':')[0:4]
			cat=cat.split('$')[1]
			family=family.split('$')[1]
			genus=genus.split('$')[1]
			species=species.split('$')[1]
		except: cat,species, genus, taxonomy = 'NA', 'NA', 'NA', 'NA'
		base=os.path.basename(input)
		virname=''
		for e in species:
			if e.isalnum(): virname+=e
			else: virname+='_'
		label = base+'_'+virname
		of = open(os.path.dirname(input)+'/aln/'+label+'.html', 'w')
		of2 = open(os.path.dirname(input)+'/tmp/'+label+'.fa', 'w')
		hitHeader(of)
		for index in cache[virus]:
			id=''
			query_nt=''
			pair_nt=''
			outrow=['<tr><td>'+virus+'<td>']
			for i in range(11):
				if i ==0: 
					continue
				out=linecache.getline(input, index+i).rstrip()
				if i==1:
					id=out.strip()
					if id.startswith('@'):
						outid=id
						paired=1
						try:
							position, pair = id.split('_')[0:2]
							if pair=='1': pp='2'
							elif pair=='2': pp='1'
							else: pass
							header=position+'_'+pp
							pair_nt= getPairSeq(header, combine, cachecombine)
							paired=len(allpairs[virus][position])
						except: pass
					else:
						outid='contig_'+'_'.join(out.split())
						paired=0
					outrow.append(outid+'<td>')
					if paired==2: outrow.append('Y<td>')
					else: outrow.append('-<td>')
					print('>'+id+' '+virname, file=of2)
				elif i==2:
					query_nt =out.strip().split()[1]
					print(linecache.getline(input, index+i).strip().split()[1], file=of2)
				elif i==3 or i==4:
					pass
				elif i==5 or i==6 or i==7:
					outrow.append(out.strip().split()[-1]+'<td>')
				elif i==8 or i==9:
					outrow.append(out[11:]+'<BR>')
				elif i==10:
					outrow.append(out[11:]+'<td>')
					nn=len(query_nt)/3
					qt = query_nt[0:nn]+'<BR>'+query_nt[nn:2*nn]+'<BR>'+query_nt[2*nn:]
					outrow.append(qt+'<td>')
					nn=len(pair_nt)/3
					pair_qt = pair_nt[0:nn]+'<BR>'+pair_nt[nn:2*nn]+'<BR>'+pair_nt[2*nn:]
					outrow.append(pair_qt+'</tr>')
					of.write(''.join(outrow)+'\n')
		of.write('</table></html>\n')
		of.close()
		of2.close()
		fain=os.path.dirname(input)+'/tmp/'+label+'.fa'
		faout=os.path.dirname(input)+'/fasta/'+label+'.fa'
		os.system(sys.executable+' '+dirscr+'sort_by_length.py '+fain+' '+faout+' False')
		counter+=1
		if combine =='--':
			#base is all_blast_filter.txt
			cmd = sys.executable+' '+dirscr+'count_by_barcode.py '+faout+' '+countfile+' '+cwd+' '+virname
			os.system(cmd)
	vcounts={}
	barcodes=set([])
	if combine =='--':
		vcounts, barcodes=readCount(countfile)
		barcodes=list(barcodes)
		barcodes=sorted(barcodes)
	return vcounts, barcodes

def readCount(countfile):
	vcounts={}
	barcodes=set([])
	f=open(countfile, 'r')
	for line in f:
		parts=line.strip().split()
		barcode, virname, count=parts
		if virname not in vcounts:
			vcounts[virname]={}
		vcounts[virname][barcode]=count
		barcodes.add(barcode)
	f.close()
	return vcounts, barcodes

if __name__ == '__main__': 
	input=sys.argv[1] #input of NR filtered blast output
	cache, VE, NE, tax, qlen, c2, c5, c10,hit_pairs =CacheLines(input)
	
	combine=sys.argv[2] #_r file combined for extracting , no len filter fasta
	dirscr=sys.argv[3]  # pasta deste script, para chamar os dois irmaos abaixo
	try: cachecombine=CacheFASTA(combine, hit_pairs) #combined fasta file cache
	except: cachecombine ={}
	base=sys.argv[4] #sorted inputfile
	cwd=sys.argv[5] #cwd
	try: outfa=sys.argv[6]; 
	except: pass
	allpairs={}
	vcounts, barcodes=OutputVirus(cache, input, allpairs, combine, cachecombine, base, cwd)
	printVirusSummary(cache, VE, NE, tax, input, qlen, c2, c5, c10, vcounts, barcodes)

/mnt/cluster/xdeng/script/schedule2.py bowtieBac.txt server.txt
wait
source bowtiesam2fq.sh  >bowtiesam2fq.log
wait
source clonetrim.sh >clonetrim.log 
wait
source skipadaptor.sh 
wait
source fq_clean.sh 
wait
source polyA_raw.sh >raw.log 
wait
source polyA_clean.sh >clean.log 
wait
echo Welcome39 |find . "*" -print0 | sudo xargs -0 chmod 777
source prep_reads.sh
wait
source combineContig_reads.sh >combine.log 
wait
/mnt/cluster/xdeng/script/schedule2.py blast_virus.txt server.txt
wait
source blast_virus_parser.sh 
wait
source mergeSig.sh 
wait
/mnt/cluster/xdeng/script/schedule2.py diamond_nr.txt server.txt
wait
source diamond_nr_filter.sh >diamondnr.log  
wait
source blast_output_merge.sh 
wait
source blast_output_sort.sh >blastsort.log 
wait
source prepBlastFile.sh 
cat *.log > stats.logg
/mnt/cluster/xdeng/script/firstpage.py no
wait
echo Welcome39 |find . "*" -print0 | sudo xargs -0 chmod 777
source movetowww.sh 
source plot_pie.sh 
source plot_poly.sh  
wait
source mergeTable.sh 
echo Welcome39 |find . "*" -print0 | sudo xargs -0 chmod 777

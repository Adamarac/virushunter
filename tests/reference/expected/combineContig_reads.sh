cat /mnt/work/fastq/S2_contig4  /mnt/work/fastq/S2.fa > /mnt/work/fastq/S2_c 
/mnt/cluster/xdeng/script/splitQuery.py /mnt/work/fastq/S2_c  50
cat /mnt/work/fastq/S1_contig4  /mnt/work/fastq/S1.fa > /mnt/work/fastq/S1_c 
/mnt/cluster/xdeng/script/splitQuery.py /mnt/work/fastq/S1_c  50

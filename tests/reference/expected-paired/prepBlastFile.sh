ssh bsidna4 "cd /mnt/work/fastq/ &&makeblastdb -dbtype nucl -parse_seqids -in S1.fa -out S1_blastdb "&
ssh bsidna5 "cd /mnt/work/fastq/ &&makeblastdb -dbtype nucl -parse_seqids -in S2.fa -out S2_blastdb "&
wait
mv fastq/*_blastdb* /mnt/work/work/blast/
/mnt/cluster/xdeng/script/blastAlias.py work /mnt/work/work/blast/

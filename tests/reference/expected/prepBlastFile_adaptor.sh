ssh bsidna4 "cd /mnt/work/fastq/ &&makeblastdb -dbtype nucl -parse_seqids -in S2_1.fa -out S2_1_blastdb && makeblastdb -dbtype nucl -parse_seqids -in S2_2.fa -out S2_2_blastdb && blastdb_aliastool -dblist 'S2_1_blastdb S2_2_blastdb' -dbtype nucl -out S2_blastdb -title 'S2_blastdb' "&
ssh bsidna5 "cd /mnt/work/fastq/ &&makeblastdb -dbtype nucl -parse_seqids -in S1_1.fa -out S1_1_blastdb && makeblastdb -dbtype nucl -parse_seqids -in S1_2.fa -out S1_2_blastdb && blastdb_aliastool -dblist 'S1_1_blastdb S1_2_blastdb' -dbtype nucl -out S1_blastdb -title 'S1_blastdb' "&
wait
mv fastq/*_blastdb* /mnt/work/blast_filter_out/blast2/

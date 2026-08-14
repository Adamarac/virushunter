ssh bsidna35 /mnt/cluster/tools/CLARKSCV1.2.3.2/exe/CLARK -k 20 -n 48 -T /mnt/cluster/xdeng/taxon/target1.txt -D /mnt/cluster/xdeng/taxon/CLARK_DB1/ -O /mnt/work/fastq/S1.fa -R /mnt/work/clark_out/S1_clark1 &
wait
ssh bsidna35 /mnt/cluster/tools/CLARKSCV1.2.3.2/exe/CLARK -k 20 -n 48 -T /mnt/cluster/xdeng/taxon/target1.txt -D /mnt/cluster/xdeng/taxon/CLARK_DB1/ -O /mnt/work/fastq/S2.fa -R /mnt/work/clark_out/S2_clark1 &
wait
ssh bsidna35 /mnt/cluster/tools/CLARKSCV1.2.3.2/exe/CLARK -k 20 -n 48 -T /mnt/cluster/xdeng/taxon/target2.txt -D /mnt/cluster/xdeng/taxon/CLARK_DB2/ -O /mnt/work/fastq/S1.fa -R /mnt/work/clark_out/S1_clark2 &
wait
ssh bsidna35 /mnt/cluster/tools/CLARKSCV1.2.3.2/exe/CLARK -k 20 -n 48 -T /mnt/cluster/xdeng/taxon/target2.txt -D /mnt/cluster/xdeng/taxon/CLARK_DB2/ -O /mnt/work/fastq/S2.fa -R /mnt/work/clark_out/S2_clark2 &
wait
ssh bsidna35 /mnt/cluster/tools/CLARKSCV1.2.3.2/exe/CLARK -k 20 -n 48 -T /mnt/cluster/xdeng/taxon/target3.txt -D /mnt/cluster/xdeng/taxon/CLARK_DB3/ -O /mnt/work/fastq/S1.fa -R /mnt/work/clark_out/S1_clark3 &
wait
ssh bsidna35 /mnt/cluster/tools/CLARKSCV1.2.3.2/exe/CLARK -k 20 -n 48 -T /mnt/cluster/xdeng/taxon/target3.txt -D /mnt/cluster/xdeng/taxon/CLARK_DB3/ -O /mnt/work/fastq/S2.fa -R /mnt/work/clark_out/S2_clark3 &
wait

ssh bsidna5 /mnt/cluster/xdeng/script/hmmer_annot.py /mnt/cluster/xdeng/blastdb/vFam/annot2014.txt /mnt/work/work/mystery/S2_m.fasta.out /mnt/work/work/mystery/S2_m.fasta.out2 /mnt/work/vfam.log &
ssh bsidna6 /mnt/cluster/xdeng/script/hmmer_annot.py /mnt/cluster/xdeng/blastdb/vFam/annot2014.txt /mnt/work/work/mystery/S1_m.fasta.out /mnt/work/work/mystery/S1_m.fasta.out2 /mnt/work/vfam.log &
cat /mnt/work/work/mystery/S2_m.fasta.out2 /mnt/work/work/mystery/S1_m.fasta.out2 > /mnt/work/work/mystery/all_m.fasta.out2

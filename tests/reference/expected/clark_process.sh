cat /mnt/work/clark_out/S2*.csv > /mnt/work/clark_out/S2.csvv 
/mnt/cluster/xdeng/script/clark_result.py /mnt/cluster/xdeng/taxon/species_index.txt /mnt/work/clark_out/S2.csvv /mnt/work/work/clark/S2.count /mnt/work/fastq/S2.fa /mnt/work/work
/mnt/cluster/xdeng/script/clark_html.py /mnt/work/work/clark/S2.count /mnt/work/work/clark/S2.count.csv /mnt/work/work/clark/S2.html 
cat /mnt/work/clark_out/S1*.csv > /mnt/work/clark_out/S1.csvv 
/mnt/cluster/xdeng/script/clark_result.py /mnt/cluster/xdeng/taxon/species_index.txt /mnt/work/clark_out/S1.csvv /mnt/work/work/clark/S1.count /mnt/work/fastq/S1.fa /mnt/work/work
/mnt/cluster/xdeng/script/clark_html.py /mnt/work/work/clark/S1.count /mnt/work/work/clark/S1.count.csv /mnt/work/work/clark/S1.html 

from lineinfile import AtEOF

line = "gnusto=cleesh"
args = {"inserter": AtEOF()}
options = ["--eof"]

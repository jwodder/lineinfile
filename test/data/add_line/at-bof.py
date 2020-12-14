from lineinfile import AtBOF

line = "gnusto=cleesh"
args = {"inserter": AtBOF()}
options = ["--bof"]

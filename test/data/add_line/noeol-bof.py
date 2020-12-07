from lineinfile import AtBOF

input_file = "input-noeol.txt"
line = "gnusto=cleesh"
args = {"locator": AtBOF()}

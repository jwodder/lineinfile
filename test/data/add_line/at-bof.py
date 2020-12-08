from lineinfile import AtBOF

line = "gnusto=cleesh"
args = {"locator": AtBOF()}
options = ["--bof"]

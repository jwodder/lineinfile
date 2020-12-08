from lineinfile import AtEOF

line = "gnusto=cleesh"
args = {"locator": AtEOF()}
options = ["--eof"]

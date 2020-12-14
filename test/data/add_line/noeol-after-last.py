from lineinfile import AfterLast

input_file = "input-noeol.txt"
line = "gnusto=cleesh"
args = {"inserter": AfterLast(r'^x=')}
options = ["-A", "^x="]

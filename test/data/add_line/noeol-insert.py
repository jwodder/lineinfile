from lineinfile import AfterFirst

input_file = "input-noeol.txt"
line = "gnusto=cleesh"
args = {"inserter": AfterFirst(r'^spaced\s*=')}
options = ["-a", r'^spaced\s*=']

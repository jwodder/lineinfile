from lineinfile import BeforeLast

line = "gnusto=cleesh"
args = {"inserter": BeforeLast(r'^foo=')}
options = ["-B", "^foo="]

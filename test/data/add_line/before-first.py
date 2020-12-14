from lineinfile import BeforeFirst

line = "gnusto=cleesh"
args = {"inserter": BeforeFirst(r'^foo=')}
options = ["-b", "^foo="]

from lineinfile import AfterLast

line = "gnusto=cleesh"
args = {"inserter": AfterLast(r'^foo=')}
options = ["-A", "^foo="]

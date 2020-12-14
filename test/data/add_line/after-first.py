from lineinfile import AfterFirst

line = "gnusto=cleesh"
args = {"inserter": AfterFirst(r'^foo=')}
options = ["-a", "^foo="]

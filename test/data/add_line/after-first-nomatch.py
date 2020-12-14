from lineinfile import AfterFirst

line = "gnusto=cleesh"
args = {"inserter": AfterFirst(r'notinfile')}
options = ["-a", "notinfile"]

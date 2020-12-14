from lineinfile import AfterFirst

line = "gnusto=cleesh"
args = {"regexp": 'notinfile', "inserter": AfterFirst(r'^foo=')}
options = ["-e", "notinfile", "-a", "^foo="]

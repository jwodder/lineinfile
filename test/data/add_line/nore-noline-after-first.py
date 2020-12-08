from lineinfile import AfterFirst

line = "gnusto=cleesh"
args = {"regexp": 'notinfile', "locator": AfterFirst(r'^foo=')}
options = ["-e", "notinfile", "-a", "^foo="]

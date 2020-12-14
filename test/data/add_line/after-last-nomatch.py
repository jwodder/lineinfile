from lineinfile import AfterLast

line = "gnusto=cleesh"
args = {"inserter": AfterLast('notinfile')}
options = ["-A", "notinfile"]

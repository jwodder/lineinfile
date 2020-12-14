from lineinfile import BeforeLast

line = "gnusto=cleesh"
args = {"inserter": BeforeLast('notinfile')}
options = ["-B", "notinfile"]

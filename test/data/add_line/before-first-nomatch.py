from lineinfile import BeforeFirst

line = "gnusto=cleesh"
args = {"inserter": BeforeFirst('notinfile')}
options = ["-b", "notinfile"]

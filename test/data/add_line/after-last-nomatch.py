from lineinfile import AfterLast

line = "gnusto=cleesh"
args = {"locator": AfterLast('notinfile')}
options = ["-A", "notinfile"]

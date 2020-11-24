from lineinfile import AfterFirst

line = "gnusto=cleesh"
args = {"locator": AfterFirst(r'notinfile')}

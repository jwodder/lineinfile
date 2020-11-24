from lineinfile import BeforeFirst

line = "gnusto=cleesh"
args = {"locator": BeforeFirst(r'^foo=')}

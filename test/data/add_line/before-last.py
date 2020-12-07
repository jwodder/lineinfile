from lineinfile import BeforeLast

line = "gnusto=cleesh"
args = {"locator": BeforeLast(r'^foo=')}

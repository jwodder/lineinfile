from lineinfile import AfterLast

line = "gnusto=cleesh"
args = {"locator": AfterLast(r'^foo=')}
options = ["-A", "^foo="]

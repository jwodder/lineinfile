from lineinfile import AfterLast

input_file = "input-noeol.txt"
line = "gnusto=cleesh"
args = {"locator": AfterLast(r'^x=')}

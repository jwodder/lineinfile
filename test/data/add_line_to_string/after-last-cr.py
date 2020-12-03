from lineinfile import AfterLast

input_file = "input-cr-diff.txt"
line = "gnusto=cleesh"
args = {"locator": AfterLast(r'=stuff$')}

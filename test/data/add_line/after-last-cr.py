from lineinfile import AfterLast

input_file = "input-cr-diff.txt"
line = "gnusto=cleesh"
args = {"inserter": AfterLast(r'=stuff$')}
options = ["-A", "=stuff$"]
nonuniversal_lines = True

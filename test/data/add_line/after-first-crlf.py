from lineinfile import AfterFirst

input_file = "input-crlf.txt"
line = "gnusto=cleesh"
args = {"inserter": AfterFirst(r'=stuff\r$')}
options = ["-a", r"=stuff\r$"]
nonuniversal_lines = True

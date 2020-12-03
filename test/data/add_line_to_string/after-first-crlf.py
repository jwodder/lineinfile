from lineinfile import AfterFirst

input_file = "input-crlf.txt"
line = "gnusto=cleesh"
args = {"locator": AfterFirst(r'=stuff\r$')}

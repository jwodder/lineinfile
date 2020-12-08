input_file = "input-crlf.txt"
line = "gnusto=cleesh"
args = {"regexp": r'=stuff\r$', "match_first": True}
options = ["-e", r'=stuff\r$', "--match-first"]
nonuniversal_lines = True

line = r'gnusto=\1:\2'
args = {"regexp": r'^(foo)=(\w+)', "backrefs": True, "match_first": True}
options = ["-e", r'^(foo)=(\w+)', "--backrefs", "--match-first"]

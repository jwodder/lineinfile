line = r'gnusto=\1:\2'
args = {"regexp": r'^(notinfile)=(\w+)', "backrefs": True}
options = ["-e", r'^(notinfile)=(\w+)', "--backrefs"]

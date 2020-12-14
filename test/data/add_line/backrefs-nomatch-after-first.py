from lineinfile import AfterFirst

line = r'gnusto=\1:\2'
args = {
    "regexp": r'^(notinfile)=(\w+)',
    "backrefs": True,
    "inserter": AfterFirst(r'^foo='),
}
options = ["-e", r'^(notinfile)=(\w+)', "--backrefs", "-a", "^foo="]

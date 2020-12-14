import re
from   lineinfile import AfterFirst

line = "gnusto=cleesh"
args = {"inserter": AfterFirst(re.compile(r'^foo='))}
options = ["--after-first", "^foo="]

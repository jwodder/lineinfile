import re
from   lineinfile import BeforeFirst

line = "gnusto=cleesh"
args = {"inserter": BeforeFirst(re.compile(r'^foo='))}
options = ["--before-first", "^foo="]

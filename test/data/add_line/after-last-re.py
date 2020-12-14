import re
from   lineinfile import AfterLast

line = "gnusto=cleesh"
args = {"inserter": AfterLast(re.compile(r'^foo='))}
options = ["--after-last", "^foo="]

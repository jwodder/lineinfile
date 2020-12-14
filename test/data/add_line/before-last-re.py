import re
from   lineinfile import BeforeLast

line = "gnusto=cleesh"
args = {"inserter": BeforeLast(re.compile(r'^foo='))}
options = ["--before-last", "^foo="]

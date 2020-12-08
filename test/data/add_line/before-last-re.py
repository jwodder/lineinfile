import re
from   lineinfile import BeforeLast

line = "gnusto=cleesh"
args = {"locator": BeforeLast(re.compile(r'^foo='))}
options = ["--before-last", "^foo="]

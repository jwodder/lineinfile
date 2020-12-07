import re
from   lineinfile import BeforeFirst

line = "gnusto=cleesh"
args = {"locator": BeforeFirst(re.compile(r'^foo='))}

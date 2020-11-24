import re
from   lineinfile import AfterLast

line = "gnusto=cleesh"
args = {"locator": AfterLast(re.compile(r'^foo='))}

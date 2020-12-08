import re

line = "gnusto=cleesh"
args = {"regexp": re.compile(r'^bar=')}
options = ["--regexp", "^bar="]

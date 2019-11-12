import sys, pandas
files = sys.argv[1:]
if len(files)<2:
  sys.exit("Need to specify at least two files!")
print("First read file " + files[0])
x = pandas.read_csv(files[0], index_col=0)
for f in files[1:]:
  print("Then add file " + f)
  y = pandas.read_csv(f, index_col=0)
  x = x.add(y, fill_value=0)
print("And finally give the output on the screen")
print(x)
x.to_csv("test_output.csv")

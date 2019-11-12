# Convert a crosstable of results to a pgn file for consumption by BayesElo
# A result of "player 1 beats player2" needs to turn into
# a line of the pgn file of the format
# [White "player 1"][Black "player 2"][Result "1-0"] 1-0

# Command line arguments should be input (csv) and output (pgn) filenames


from __future__ import print_function
import sys, os, pandas
if (len(sys.argv) != 3):
  print ("Usage: python input.csv output.pgn")
infile = sys.argv[1]
outfile = sys.argv[2]
if os.path.exists(outfile):
  sys.exit("Error : file " + outfile + " already exists.")
outstream = open(outfile, "w")

crosstable = pandas.read_csv(infile, index_col=0)

ngames = 0
for prog1 in list(crosstable):
  for prog2 in list(crosstable):
    for i in range(int(crosstable.loc[prog1][prog2])):
      outstream.write('[White "' + prog1 + '"][Black "' + prog2 + '"][Result "1-0"] 1-0\n')
      ngames+=1

outstream.close()
print("Created file "+outfile+" with "+str(ngames)+" games")

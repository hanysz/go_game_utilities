# Convert a folder full of sgf files to pgn so that BayesElo can read them.

import sys, os, glob, re

if (len(sys.argv) != 3):
  print ("Usage: python sgf_to_pgn.py foldername outputname")
input_folder = sys.argv[1]
output_file = sys.argv[2]

if (os.path.exists(output_file)):
  sys.exit("File " + output_file + " already exists.  No new output created.")

outstream = open(output_file, "w")
sgf_list = glob.glob(input_folder + "/*.sgf")
if len(sgf_list)==0:
  sys.exit("Can't find any SGF files in " + input_folder)

for f in sgf_list:
  sgf = open(f,'r').read()
  white_name = re.search("PW\[.*?\]",sgf)
  if white_name==None:
    print(f + ": can't find name of white player -- skipping this game")
    continue
  else:
    white_name = white_name.group(0)[3:-1]
  black_name = re.search("PB\[.*?\]",sgf)
  if black_name==None:
    print(f + ": can't find name of black player -- skipping this game")
    continue
  else:
    black_name = black_name.group(0)[3:-1]
  winner = re.search("RE\[.*?\]",sgf)
  if winner==None:
    print(f + " doesn't contain a RE[..] tag: skipping this game")
    continue
  else:
    winner = winner.group(0)[3]
  if winner=="W":
    outstream.write('[White "' + white_name + '"][Black "' + black_name + '"][Result "1-0"] 1-0\n')
  else:
    outstream.write('[White "' + white_name + '"][Black "' + black_name + '"][Result "0-1"] 0-1\n')
  
outstream.close()

# Rename players:
# in the specified folder, we want to change the name in:
#  all CSV files
#  all PGN files
# and create/update a rename log to track what's been done when
# Don't change SGF files

import sys, os, datetime, glob, re

if (len(sys.argv) != 3):
  print ("Usage: python rename_players.py renamelist directory")

renamelist = sys.argv[1]
basedir = sys.argv[2] + "/"

name_pairs = tuple(open(renamelist, "r"))
if len(name_pairs) == 0:
  sys.exit("File " + renamelist + " is empty!")
for p in name_pairs:
  if len(p.split()) !=2:
    sys.exit("Each line of " + renamelist + " must contain exactly two names!\n" +
             "Bad line: " + p)
name_pairs = [p.split() for p in name_pairs]

# nb some of the old names contain a + which is treated as a special character by regex
for p in name_pairs:
  if p[0]=="oakfoam+book":
    p[0]="oakfoam\+book"
  if p[0]=="gnugo+cache":
    p[0]="gnugo\+cache"

logfile = open(basedir+"rename_log", "a")
logfile.write("Renaming at " + str(datetime.datetime.now())[0:16] + ":\n")

# To do:
#   loop through all CSV files in the folder
#   replace ^p1, with ^p2,
#   replace ,p1, with ,p2,
#   replace ,p1$ with ,p2$
#   loop through all PGN files, replace "p1" with "p2"

# CSV files:
for csv in glob.glob(basedir+"*.csv"):
  f = open(csv, 'r+')
  contents = f.read()
  # do search and replace
  for p in name_pairs:
    contents = re.sub("^"+p[0]+",", p[1]+",", contents, flags=re.M)
    contents = re.sub(","+p[0]+",", ","+p[1]+",", contents, flags=re.M)
    contents = re.sub(","+p[0]+"$", ","+p[1], contents, flags=re.M)
  f.seek(0) # back to beginning of file ready to overwrite
  f.write(contents)
  f.truncate()
  f.close()

for pgn in glob.glob(basedir+"*.pgn"):
  f = open(pgn, 'r+')
  contents = f.read()
  # do search and replace
  for p in name_pairs:
    contents = re.sub('"'+p[0]+'"', '"'+p[1]+'"', contents, flags=re.M)
  f.seek(0) # back to beginning of file ready to overwrite
  f.write(contents)
  f.truncate()
  f.close()


for p in name_pairs:
  logfile.write("  " + p[0] + " -> " + p[1] + "\n")
logfile.close()

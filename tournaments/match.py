# Play a game or match between two programs
# Initial version: visible in gogui
# Later we'll add flags for number of games, invisible, options for where to save SGF, etc
# and need to add cleanup of gogui-twogtp output files

# Plan to write other scripts for round robin or lineup format tournaments,
# as well as automatic Bayeselo calculations where possible

# First, usage will be
#  python match.py prog1 prog2 t
#  where t is total time per player in minutes
#  prog1 plays white

# Current options for prog1 and prog2 are
# fuego, gnugo, leela, pachi, pachi_dcnn

from __future__ import print_function
import sys, os, datetime
if (len(sys.argv) != 4):
  print ("Usage: python match.py prog1 prog2 t")
prog1 = sys.argv[1]
prog2 = sys.argv[2]
t = sys.argv[3]

def get_command(progname):
  filename = "command_lines/"+progname
  command = tuple(open(filename, 'r'))[1]
  command = command.replace('Command: ', '')
  command = command.replace('\n', '')
  return(command)

#def command_line(prog1, prog2):
  #return(

visible = True
if visible:
  command_line = 'gogui -size 19 -program "gogui-twogtp -white \\"' + \
  get_command(prog1) + '\\" -black \\"' + get_command(prog2) + \
  '\\" -time ' + t + ' -komi 7.5 -games 1 -sgffile test.sgf" -computer-both -auto'
else:
  command_line = 'gogui-twogtp -white "' + \
  get_command(prog1) + '" -black "' + get_command(prog2) + \
  '" -time ' + t + ' -komi 7.5 -games 1 -sgffile test.sgf -auto'

print (prog1 + " vs " + prog2 + ": ", end ='')
print(command_line)
os.system(command_line)

timestamp = str(datetime.datetime.now())[0:16]
# This is in the format '2018-08-29 12:46'
# Turn it into something more friendly as a linux filename
timestamp = timestamp.replace(' ', '_').replace(':','-')
sgf_filename = prog1 + "-" + prog2 + "-" + timestamp + ".sgf"
os.rename("test.sgf-0.sgf", sgf_filename)

resultline = tuple(open('test.sgf.dat', 'r'))[-1]

def get_result(resultline, gameID):
# resultline is a string that looks something like
# 0	B+13.5	B+13.5	?	0	-	 other stuff
# which is tab separated
# gameID is to be printed if there is a warning or error message
# Return:
#   1 if fields 2 and 3 both start with W+
#   0 if fields 2 and 3 both start with B+
#   -1 if disagreement (one W+, one B+, either way round)
#  exit if either fails to start with one of W+ or B+
#  print warning if disagreement on either the winner or the margin (the bit after the +)
  resultitems = resultline.split('\t')
  winner1 = resultitems[1][0]
  winner2 = resultitems[2][0]
  margin1 = resultitems[1][1:]
  margin2 = resultitems[2][1:]
  if (winner1 not in ['B', 'W']) | (winner2 not in ['B', 'W']):
    print("Warning: could not extract result for game " + gameID +
             " with result string:\n" + resultline)
    return -1
  if winner1 != winner2:
    print("Disputed result for " + gameID + ", not counted in cross table")
    return -1
  if margin1 != margin2:
    print("Warning: agreed winner but disputed score for " + gameID)
  if winner1 == 'W':
    return 1
  else:
    return 0

result = get_result(resultline, sgf_filename)
if result==1:
  print(prog1 + " wins")
elif result==0:
  print(prog2 + " wins")
else:
  print("Result unknown")
print("")
os.remove('test.sgf.dat')


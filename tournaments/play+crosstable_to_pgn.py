# To do:
#  play matilda vs matilda and matilda vs weak gnugo to get it to finish + score some games
#  download some other engines in between leela and pachi
#  try some 5 min games

# Play a game or match between some programs
# Possible modes:
#  round-robin: all play all n times (n is even, play as both black and white)
#  match: two programs play each other exclusively n times
#  line-up: first program plays each of the others n times
# Read format, program names and time limit from a config file
# Output a crosstable and put away the SGFs nicely

# Usage:
#   python match.py config_file
# Example config file:
#   Format: round-robin
#   Games: 4
#   Time: 5
#   Sleep: 60
#   Players: gnugo pachi fuego

# Time is minutes per player per game
# Sleep is seconds to pause at end of game (to avoid overheating)
# Set sleep to 0 if overheating is not an issue

# Current options for players
# fuego, gnugo, gnugo+cache, leela, pachi, pachi_dcnn

from __future__ import print_function
import sys, os, random, pandas, numpy, datetime, time, shutil


def get_arg(config_array, pos, name):
  arg = config_array[pos]
  arg = arg.replace(name+": ", '').replace('\n', '')
  return(arg)

def make_timestamp():
  return str(datetime.datetime.now())[0:16].replace(' ', '_').replace(':','-')

def current_time():
  return str(datetime.datetime.now())[11:16]

def log(message, newline=True):
  print(message, end='')
  logfile.write(message)
  if newline:
    print('\n')
    logfile.write('\n')

def get_command(progname):
  filename = "command_lines/"+progname
  if (os.path.exists(filename)):
    command = tuple(open(filename, 'r'))[1]
  else:
    sys.exit("No command line found for program "+progname)
  command = command.replace('Command: ', '')
  command = command.replace('\n', '')
  return(command)

def make_command_line(prog1, prog2):
  return('gogui-twogtp -white "' +
         get_command(prog1) + '" -black "' + get_command(prog2) +
         '" -time ' + time_limit + ' -komi 7.5 -games 1 -sgffile test.sgf -auto'
	 )

def get_metadata(resultline):
# resultline is a string that looks something like
# 0     B+13.5  B+13.5  ?       0       -        other stuff
# which is tab separated
# Return a string of metadata:
# number of moves, time taken by each player, warn if time > time limit
  resultitems = resultline.split('\t')
  num_moves = resultitems[6]
  time_b = resultitems[7]
  time_w = resultitems[8]
  metadata = num_moves + " moves; black " + time_b + " seconds; white " + \
                                            time_w + " seconds."
  if float(time_b) > float(time_limit)*60:
    metadata += "\nBlack was over time!"
  if float(time_w) > float(time_limit)*60:
    metadata += "\nWhite was over time!"
  return metadata

def get_result(resultline, gameID):
# resultline is a string that looks something like
# 0     B+13.5  B+13.5  ?       0       -        other stuff
# which is tab separated
# gameID is to be printed if there is a warning or error message
# Return:
#   1 if fields 2 and 3 both start with W+
#   0 if fields 2 and 3 both start with B+
#   -1 if disagreement (one W+, one B+, either way round)
#  warn if either fails to start with one of W+ or B+
#  print warning if disagreement on either the winner or the margin (the bit after the +)
  resultitems = resultline.split('\t')
  winner1 = resultitems[1][0]
  winner2 = resultitems[2][0]
  margin1 = resultitems[1][1:]
  margin2 = resultitems[2][1:]
  if (winner1 not in ['B', 'W', '?']) | (winner2 not in ['B', 'W', '?']):
    log("Warning: could not extract result for game " + gameID +
             " with result string:\n" + resultline)
    return -1
  # If one player (usually fuego) puts the result as "?", then we trust the other result
  if winner1 == '?':
    if winner2 == '?':
      log("Both players gave result=? for " + gameID + ", not counted in cross table")
      return -1
    else:
      winner1=winner2
  if winner2 == '?':
    winner2=winner1
  if winner1 != winner2:
    log("Disputed result for " + gameID + ", not counted in cross table")
    return -1
  if margin1 != margin2:
    log("Warning: agreed winner but disputed score for " + gameID)
    # Note: this will also come up if one but not the othe player had result=?
    # because in that case, the margin will be blank
  if winner1 == 'W':
    return 1
  else:
    return 0

def play_game(prog1, prog2):
  command_line = make_command_line(prog1, prog2)
  log(current_time() + " Starting " + prog1 + " vs " + prog2 + ": ", newline=False)
  sys.stdout.flush() # make results of print statement visible!
  #print(command_line)
  #print("")
  os.system(command_line)
  log(" " + current_time() + " ", newline=False)

  sgf_filename = basedir + "sgf/" + prog1 + "-" + prog2 + "-" + make_timestamp() + ".sgf"
  os.rename("test.sgf-0.sgf", sgf_filename)

  resultline = tuple(open('test.sgf.dat', 'r'))[-1]
  result = get_result(resultline, sgf_filename)
  if result==1:
    log(prog1 + " wins")
    crosstable.loc[prog1][prog2] += 1
  elif result==0:
    log(prog2 + " wins")
    crosstable.loc[prog2][prog1] += 1
  else:
    log("Result unknown")
  log(get_metadata(resultline))
  os.remove('test.sgf.dat')
  time.sleep(sleep_time)














#outfile = basedir + "results-"+time_limit+"_min"+make_timestamp()
#crosstable.to_csv(outfile + ".csv")

# Back up master crosstable, then update with new results
#master_filename = basedir + "total_crosstable.csv"
#backupname = basedir + "old_crosstables/crosstable_backup-"+make_timestamp()+".csv"
#shutil.copy(master_filename, backupname)
#master = pandas.read_csv(master_filename, index_col=0)
#master.add(crosstable, fill_value=0).to_csv(master_filename)

outfile="5_min/results-5_min2018-09-01_02-21"
crosstable = pandas.read_csv(outfile+".csv", index_col=0)
# Write results to pgn so that BayesElo can read them
outstream = open(outfile + ".pgn", "w")
ngames = 0
for prog1 in list(crosstable):
  for prog2 in list(crosstable):
    for i in range(int(crosstable.loc[prog1][prog2])):
      outstream.write('[White "' + prog1 + '"][Black "' + prog2 + '"][Result "1-0"] 1-0\n')
      ngames+=1
outstream.close()
      

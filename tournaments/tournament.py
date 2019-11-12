# -*- coding: latin-1 -*-
# above line needed because there's a °C in a later comment!

# To do: strip whitespace from player name list (otherwise it fails if there's a trailing space)

from __future__ import print_function

# Max temperatures: wait until system has cooled between games
#CPU_MAX_T = 35.0
#GPU_MAX_T = 35.0 # this worked for driver version 390
GPU_MAX_T = 50.0 # after upgrading to driver 410.73, the card tends to run at 47 degrees when idle
CPU_MAX_T = 40.0
#CPU_MAX_T = 45.0 # for 1-minute games, don't need as much cooldown
#GPU_MAX_T = 45.0

# Play a game or match between some programs
# Possible modes:
#  round-robin: all play all n times (n is even, play as both black and white)
#  match: two programs play each other exclusively n times
#  line-up: first program plays each of the others n times
# Read format, program names and time limit from a config file
# Output a crosstable and put away the SGFs nicely

# Usage:
#   python tournament.py config_file
# Example config file:
#   Format: round-robin
#   Games: 4
#   Time: 5
#   Sleep: 60
#   Players: gnugo pachi fuego

# Time is minutes per player per game
# Sleep is seconds to pause at end of game (to avoid overheating)
# Set sleep to 0 if overheating is not an issue
# Update: now it rests based on temperature not time, so sleep parameter is ignored

# Current options for players
# fuego, gnugo, gnugo+cache, leela, pachi, pachi_dcnn

import sys, os, random, pandas, numpy, datetime, time, shutil, subprocess, StringIO

verbose=False # if true, then engine output will be included in SGF file comments,
              # which leads to some massive SGF files
#verbose=True

def get_arg(config_array, pos, name):
  arg = config_array[pos]
  arg = arg.replace(name+": ", '').replace('\n', '')
  return(arg)

def make_timestamp():
  return str(datetime.datetime.now())[0:16].replace(' ', '_').replace(':','-')

def current_time():
  return str(datetime.datetime.now())[11:16]

def temperature_OK(cpu_max, gpu_max):
  # return false if either temperature is above max
  cpu_temp = subprocess.check_output("sensors", shell=True)\
    .split('\n')[38].split()[1]
  gpu_temp = subprocess.check_output("nvidia-smi", shell=True)\
    .split('\n')[8].split()[2]
  cpu_temp = cpu_temp[1:-3] # remove the + at the start and the °C at the end
  gpu_temp = gpu_temp[:-1] # remove the C at the end
  return ((float(cpu_temp) <= cpu_max) & (float(gpu_temp) <= gpu_max))

def temperature():
  cpu_temp = subprocess.check_output("sensors", shell=True)\
    .split('\n')[38].split()[1]
  gpu_temp = subprocess.check_output("nvidia-smi", shell=True)\
    .split('\n')[8].split()[2]

  return("CPU " + cpu_temp + "   GPU " + gpu_temp)


def log(message, newline=True):
  print(message, end='')
  logfile = open(logfilename, "a")
  logfile.write(message)
  if newline:
    print('\n')
    logfile.write('\n')
  logfile.close()

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
  if verbose:
    return('gogui-twogtp -white "' +
         get_command(prog1) + '" -black "' + get_command(prog2) +
         '" -time ' + time_limit + ' -komi 7.5 -games 1 -sgffile test.sgf -auto' +
	 ' -debugtocomment'
	 )
  else:
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

  # If necessary, wait until cpu/gpu are cool enough:
  while True:
    log("    " + current_time() + " " + temperature())
    if temperature_OK(CPU_MAX_T, GPU_MAX_T):
      break
    else:
      time.sleep(60)

  log("Starting " + prog1 + " vs " + prog2 + ": ", newline=False)
  sys.stdout.flush() # make results of print statement visible!
  #print(command_line)
  #print("")
  os.system(command_line)
  #log(" " + current_time() + " ", newline=False)

  sgf_filename = basedir + "/sgf/" + prog1 + "-" + prog2 + "-" + make_timestamp() + ".sgf"
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
  log("")
  os.remove('test.sgf.dat')
  # time.sleep(sleep_time) -- not needed now we're waiting based on temperature


def get_ratings(results_dir, avg=2000):
# results_dir contains a number of pgn files with results
# Output: a pandas data frame with the ratings
# The average rating will be equal to the "avg" parameter
  bayes_proc = subprocess.Popen(["/home/alex/bin/bayeselo"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE)

  os.system("cat " + results_dir + "/*.pgn > bayeselo_temp_input.pgn")
  bayes_proc.stdin.write("readpgn bayeselo_temp_input.pgn\n")
  bayes_proc.stdin.write("elo\n")
  bayes_proc.stdin.write("offset " + str(avg) + "\n")
  bayes_proc.stdin.write("advantage 0\n")
  bayes_proc.stdin.write("drawelo 0.01\n")
  bayes_proc.stdin.write("mm\n")
  bayes_proc.stdin.write("exactdist\n")
  bayes_proc.stdin.write("ratings\n")
  bayes_proc.stdin.write("x\n")
  bayes_proc.stdin.write("x\n")


  while bayes_proc.returncode is None:
      bayes_proc.poll()
  ranks = bayes_proc.stdout.read()
  os.remove("bayeselo_temp_input.pgn")

  # Find the table header, then delete everything before that
  i = ranks.find("oppo. draw")
  ranks = ranks[i+13:]
  i = ranks.find("ResultSet")
  ranks = ranks[:i-1]
  # Need to attach a "read" method to the rank string so that pandas can parse it
  rank_input = StringIO.StringIO(ranks)
  df = pandas.read_csv(rank_input, sep="\s+", index_col=0, header=None)
  df.columns=["Name", "Elo", "Elo+", "Elo-", "games", "score", "avg_opp", "draws"]
  # Drop the "draws" column
  df.drop(df.columns[7], axis=1, inplace=True)

  return(df)

def get_anchored_ratings(results_dir, player, anchor):
# like get_ratings, but offset so that rating of named player=anchor
# Do this by calling get_ratings once to figure out what the offset needs to be,
# then a second time with the desired offset
  df = get_ratings(results_dir, avg=0)
  player_rating = int(df[df.Name==player]["Elo"])
  return(get_ratings(results_dir, avg=anchor-player_rating))


if (len(sys.argv) != 2):
  print ("Usage: python tournament.py config_filename")
config_filename = sys.argv[1]

if (os.path.exists(config_filename)):
  config = tuple(open(config_filename, 'r'))
else:
  sys.exit(config_filename + ": file not found:")

format = get_arg(config, 0, "Format")
if format not in ["round-robin", "match", "lineup"]:
  sys.exit("Format " + format + " not recognised.")
games = get_arg(config, 1, "Games")
ngames = int(games)
if ngames % 2 !=0:
  sys.exit("Number of games must be even, got " + games)
ngames = ngames/2 # This is the number of games with one choice of colours
time_limit = get_arg(config, 2, "Time")
basedir = time_limit+"_min" # output files go in this directory
sleep_time = float(get_arg(config, 3, "Sleep"))
playernames = get_arg(config, 4, "Players")
players = playernames.split(" ")
nplayers = len(players)

# Verify that all player names are valid:
for p in players:
  get_command(p)

start_time = make_timestamp()
logfilename = basedir + "/log_" + start_time
# logfile = open(logfilename, "w") -- move this to the log() function,
# and open/close the file for each line,
# so that messages are kept even if there's a crash or interruption


log(format + " tournament with " + games + " games per round, " +
      time_limit + " min per player per game.")
log("Players: " + playernames)
if nplayers<2:
  sys.exit("Not enough players!")
if (nplayers==2) & (format!="match"):
  log("Warning: playing a non-match format with only two players!")



crosstable = pandas.DataFrame(
  numpy.zeros((nplayers, nplayers)), index=players, columns=players
  )

if format=="round-robin":
  for p1 in range(nplayers):
    for p2 in range(nplayers):
      if p1 != p2:
	for g in range(ngames):
	  play_game(players[p1], players[p2])
elif format == "lineup":
  for p2 in range(1, nplayers):
    for g in range(ngames):
      play_game(players[0], players[p2])
      play_game(players[p2], players[0])
elif format == "match":
  for g in range(ngames):
    play_game(players[0], players[1])
    play_game(players[1], players[0])
else:
  sys.exit("Format " + format + " not recognised.")

log("Finished! \n")

outfile = basedir + "/results-"+time_limit+"_min"+start_time
crosstable.to_csv(outfile + ".csv")

# Back up master crosstable, then update with new results
master_filename = basedir + "/total_crosstable.csv"
backupname = basedir + "/old_crosstables/crosstable_backup-"+start_time+".csv"
shutil.copy(master_filename, backupname)
master = pandas.read_csv(master_filename, index_col=0)
master = master.add(crosstable, fill_value=0)
master.to_csv(master_filename)

# Write results to pgn so that BayesElo can read them
outstream = open(outfile + ".pgn", "w")
ngames = 0
for prog1 in list(crosstable):
  for prog2 in list(crosstable):
    for i in range(int(crosstable.loc[prog1][prog2])):
      outstream.write('[White "' + prog1 + '"][Black "' + prog2 + '"][Result "1-0"] 1-0\n')
      ngames+=1
outstream.close()
      
log("Created file "+outfile+".csv and " + outfile + ".pgn with "+str(ngames)+" games")
# logfile.close() -- no longer needed, this is now done inside the log() function


######################################




if time_limit <= 5:
  ratings_df = get_anchored_ratings(basedir, 'gnugo', 1500)
else:
  ratings_df = get_anchored_ratings(basedir, 'pachi_nn', 2400)

playernames = ratings_df['Name'].tolist() # Overwrite the previous value of playernames:
# this value has all players in the master crosstable,
# ordered from highest value to lowest

# In the master crosstable, replace any blank cells by zeros:
master.fillna(0, inplace=True)

# Set an index so that we can easily look things up (wins/losses below)
master['Name'] = master.columns.tolist()
master.set_index('Name', inplace=True)

# Create results_df which is the same data as master but formatted differently
# Want to get the crosstable into "k/n" form (e.g. 5/7, played 7 won 5)
results_df = pandas.DataFrame("", index=playernames, columns=['Name'] + playernames)
results_df['Name']=playernames
for p1 in playernames:
  for p2 in playernames:
    if p1==p2:
      score="-"
    else:
      wins = int(master.loc[p1][p2])
      losses = int(master.loc[p2][p1])
      if wins+losses==0:
        score="-"
      else:
        score = str(wins) + "/" + str(wins+losses)
    results_df.loc[p1][p2]=score


outfile = basedir+"/ratings.csv"
pandas.merge(ratings_df, results_df, on="Name", how='outer').to_csv(outfile, index=False)
print("To view ratings, use: libreoffice --calc --nologo " + outfile + " &")

# need time between writing output file and opening libreoffice,
# otherwise we get the old version opened!
#time.sleep(2.0)
#subprocess.Popen(["libreoffice --calc --nologo " + outfile], shell=True)


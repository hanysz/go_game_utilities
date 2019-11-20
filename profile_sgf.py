
# Turn an SGF file into a "profile file".
# The profile file is a CSV with one row per move for the selected colour,
# and the following columns:
#  move_num, game_move, game_policy, game_winrate, best_move, best_policy, best_winrate
#  opening, midgame, endgame, intuition_error, reading_error

# I'll do some follow-up analysis in R to turn this into some profile stats
# inspired by https://lifein19x19.com/viewtopic.php?f=10&t=17045

# First version, not much error checking,
# only works with even games with no passes in the game record
# May crash on games of only 1 or two moves
# May spin into an infinite loop if the engine crashes
# Will give nonsense results if the bot decides to resign at any point

# Nb this is Python3 not Python2!

# Before running this, edit the "engine_command=" line below with the path
# to your Leela Zero executable.

# Usage:
#   python profile_sgf.py filename.sgf colour playouts
# where:
#   filename.sgf is the input game file
#    (output will be stored in filename.csv and filename.log)
#   colour is b or w to specify which player's moves should be analysed
#   playouts is a number: how many playouts per move to use for analysis.

import sys, os, shlex, string
from sgfmill import sgf
# Handy reference: https://mjw.woodcraft.me.uk/sgfmill/doc/1.1.1/examples.html
from subprocess import Popen, PIPE, STDOUT

temp_filename = "LZlog"
engine_command = "/opt/leelaz/leelaz17/src/leelaz --threads 2 -r 1 --noponder -w /opt/leelaz/networks/d351f06e-192x15-2018-07-18.gz -l " + temp_filename # Using network number 157
#engine_command = "/opt/leelaz/leelaz17/src/leelaz --threads 2 -r 1 --noponder -w /opt/leelaz/networks/b3b00c6d-128x6-2018-03-04.gz -l " + temp_filename # Using small network for fast testing


error_ratio = 0.8 # moves where game winrate/LZ winrate < ratio are classed as errors
#error_ratio = 0.95 # moves where game winrate/LZ winrate < ratio are classed as errors
intuition_threshold = 20 # moves with policy net value >= 20% are classed as "good intuition"

opening_threshold = 30 # first 30 moves of the game are considered "opening"
endgame_threshold = 120 # moves 121 onwards are considered "endgame"

if (len(sys.argv) != 4):
  sys.exit("Usage: python profile_sgf.py filename.sgf colour playouts")

input_filename = sys.argv[1]
colour = sys.argv[2]
playouts = sys.argv[3]

if colour not in ['b', 'w']:
  sys.exit("Error: colour " + colour + " should be either b or w")

if (os.path.exists(temp_filename)):
  sys.exit("Error: need to use filename " + temp_filename + " as temporary storage, but there's already something there.")
if (not os.path.exists(input_filename)):
  sys.exit("Error: input file " + input_filename + " does not exist.")
output_filename = input_filename[:-3]+"csv" # being lazy, no sanity checking here
log_filename = input_filename[:-3]+"txt"
if (os.path.exists(output_filename)):
  sys.exit("Error: output file " + output_filename + " already exists.")
if (os.path.exists(log_filename)):
  sys.exit("Error: log file " + log_filename + " already exists.")

with open(input_filename, "rb") as f:
  game = sgf.Sgf_game.from_bytes(f.read())
root_node = game.get_root()

board_letters = string.ascii_lowercase # 'a' to 'z'
board_letters = board_letters.replace("i", "") # 'i' isn't used as a coordinate
board_LETTERS = string.ascii_uppercase # 'a' to 'z'
board_LETTERS = board_LETTERS.replace("I", "") # 'i' isn't used as a coordinate

def move_to_gtp(m):
  # m is a move returned by sgfmill's get_move,
  # i.e. it's a tuple (colour, (up, across))
  # Return as a text string so we can give it to LZ as a gtp command
  return("play " + m[0] + " " + board_letters[m[1][1]] + str(m[1][0]+1))

def move_to_text(m):
  return(board_LETTERS[m[1][1]] + str(m[1][0]+1))

def text_of_move_num(n):
  # move number n as a text string
  return(move_to_text(game.get_main_sequence()[n].get_move()))

logfile = open(log_filename, "a")
logfile.write(root_node.get("PW") + "-" + root_node.get("PB") + ", ")
game_length = len(game.get_main_sequence())-1
logfile.write(str(game_length) + " moves.\n")
logfile.write("Engine command: " + engine_command + "\n")
logfile.write("Analysing for " + colour + " with " + playouts + " playouts per move.\n")
logfile.write("Error ratio: " + str(error_ratio) +
                "; intuition threshold " + str(intuition_threshold) + ".\n")
logfile.write("Middlegame is moves " + str(opening_threshold+1) + " to " +
                str(endgame_threshold) + ".\n")
logfile.close()

p = Popen(shlex.split(engine_command), stdout=PIPE, stdin=PIPE, stderr=PIPE)
p.stdin.write(b'time_settings 0 1 0\n') # Turn off time management
p.stdin.write(bytes('lz-setoption name playouts value ' + playouts + '\n', "utf-8"))

to_play = 'b'
move_num = 1
start_move = 1
def flip_colour(c):
  if c == 'b':
    return 'w'
  else:
    return 'b'
if colour == 'w':
  # Put black's first move on the board before starting analysis
  first_move = game.get_main_sequence()[1].get_move()
  p.stdin.write(bytes(move_to_gtp(first_move) + '\n', "utf-8"))
  move_num = 2
  to_play = 'w'
  start_move = 2
  
for node in game.get_main_sequence()[start_move:]:
   if node.get_move()[0] is None or node.get_move()[1] is None:
   # passes probably indicate the end of the game
     break
   p.stdin.write(bytes('genmove ' + to_play + '\n', "utf-8"))
   to_play = flip_colour(to_play)
   p.stdin.write(b'undo\n')
   p.stdin.write(bytes(move_to_gtp(node.get_move()) + '\n', "utf-8"))

p.communicate() # This will end the LZ process

tempfile = open(temp_filename, "r")
outfile = open(output_filename, "w")
outfile.write("move_num,game_move,game_policy,game_winrate,")
outfile.write("best_move,best_policy,best_winrate,")
outfile.write("opening,midgame,endgame,intuition_error,reading_error\n")

line = tempfile.readline()
finished = False
actual = False # alternate between analysis of actual game moves and LZ preferred moves
while not finished:
  while not line.startswith("Thinking"):
    line = tempfile.readline()
    if not line: # reached end of file
      finished = True
      break
  # There may be some update lines that we want to skip.  Find the next blank line:
  while line != "\n":
    line = tempfile.readline()
    if not line: # reached end of file
      finished = True
      break
  line = tempfile.readline() # Get the line after the blank line.
  # After the above statement, 'line' contains LZ's preferred move.
  topmove = True
  game_move = text_of_move_num(move_num)
  while line.startswith(" "):
    words = line.split()
    movetext = words[0]
    value = words[4]
    value = value[:-2] # remove trailing %) characters
    policy = words[8][:-2]

    if not actual:
      if topmove:
        got_policy = False
        best_move = movetext
        best_value = value
        best_policy = policy
        topmove = False
      if movetext == game_move:
        game_policy = policy
        got_policy = True
    else:
      if topmove:
        game_value = str(100-float(value))
        if not got_policy:
          game_policy = -1
        topmove = False
        got_policy = False

    line = tempfile.readline()
    if not line: # reached end of file
      finished = True
      break

  if actual:
    # Determine if the move was an error, and if so then output details
    if float(game_value)/float(best_value) < error_ratio:
      if float(game_policy) < 0:
        policy_text = "NA"
      else:
        policy_text = str(game_policy)
      outfile.write(str(move_num)+","+game_move+","+policy_text+","+game_value+",")
      outfile.write(best_move+","+best_policy+","+best_value+",")
      if move_num <= opening_threshold:
        outfile.write("1,0,0,") # opening, not middlegame, not endgame
      elif move_num <= endgame_threshold:
        outfile.write("0,1,0,")
      else:
        outfile.write("0,0,1,")
      if float(game_policy) >= intuition_threshold:
        outfile.write("0,1") # reading error, not intuition error
      elif float(best_policy) >= intuition_threshold:
        outfile.write("1,0") # game_policy is below threshold => intuition error
      else:
        outfile.write("0,0") # can't distinguish error type in this case
      outfile.write("\n")

    move_num += 2
    if move_num > game_length:
      finished = True

  actual = not actual # alternate between actual game and LZ-recommended moves
tempfile.close()
outfile.close()
os.remove(temp_filename)



# Turn an SGF file into a temperature graph
# See discussion at https://lifein19x19.com/viewtopic.php?f=15&t=17069

# Nb this is Python3 not Python2!

# Before running this, edit the "engine_command=" line below with the path
# to your KataGo executable.

# Modified for environmental go games:
#   track the "card temperature" as well as the game temperate
#   each pass means that the card temperature goes down half a point
#     add the card temperature to the graph

# Second version, calculate Bill Spight's adjusted temperatures too
# Also modify to accept passes during the game
# (mainly so that we can analyse the environmental go game
# at http://britgo.org/results/env/index.html)

# First version, not much error checking,
# only works with even games with no passes in the game record
# May crash on games of only 1 or two moves
# May spin into an infinite loop if the engine crashes
# Will give nonsense results if the bot decides to resign at any point

# Usage:
#   python temperature_graph.py filename.sgf time
# where:
#   filename.sgf is the input game file
#    (output will be stored in filename.csv, filename.log and filename.jpg)
#   time is a number: upper limit on how many seconds to spend on analysis
#   (usually finishes a bit more quickly, except for very long games)

import sys, os, shlex, string, re, pandas, math
from sgfmill import sgf
# Handy reference: https://mjw.woodcraft.me.uk/sgfmill/doc/1.1.1/examples.html
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
from subprocess import Popen, PIPE, STDOUT

temp_filename = "gtp.log" # hard-coded into KataGo, can't easily change the name
engine_command = "/opt/katago/katago gtp -model /opt/katago/b20_model/model.txt.gz -config /opt/katago/gtp_example.cfg"

if (len(sys.argv) != 3):
  sys.exit("Usage: python temperature_graph.py filename.sgf time_in_seconds")

input_filename = sys.argv[1]
time_limit = int(sys.argv[2])//2

if (os.path.exists(temp_filename)):
  sys.exit("Error: need to use filename " + temp_filename + " as temporary storage, but there's already something there.")
if (not os.path.exists(input_filename)):
  sys.exit("Error: input file " + input_filename + " does not exist.")
output_filename = input_filename[:-3]+"csv" # being lazy, no sanity checking here
log_filename = input_filename[:-3]+"txt"
image_filename = input_filename[:-3]+"jpg"
if (os.path.exists(output_filename)):
  sys.exit("Error: output file " + output_filename + " already exists.")
if (os.path.exists(log_filename)):
  sys.exit("Error: log file " + log_filename + " already exists.")
if (os.path.exists(image_filename)):
  sys.exit("Error: image file " + image_filename + " already exists.")

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
  # Return as a text string so we can give it to KataGo as a gtp command
  return("play " + m[0] + " " + board_letters[m[1][1]] + str(m[1][0]+1))

def move_to_text(m):
  if m[1] is None:
    return "pass"
  else:
    return(board_LETTERS[m[1][1]] + str(m[1][0]+1))

def text_of_move_num(n):
  # move number n as a text string
  return(move_to_text(game.get_main_sequence()[n].get_move()))

logfile = open(log_filename, "a")
logfile.write(root_node.get("PW") + "-" + root_node.get("PB") + ", ")
game_length = len(game.get_main_sequence())-1
logfile.write(str(game_length) + " moves.\n")
logfile.write("Engine command: " + engine_command + "\n")
logfile.write("Analysing with " + str(time_limit) + " seconds per player.\n")
logfile.close()

p = Popen(shlex.split(engine_command), stdout=PIPE, stdin=PIPE, stderr=PIPE)
time_string = "time_settings " + str(time_limit) + " 0 0\n"
p.stdin.write(bytes(time_string, "utf-8"))

move_num = 1
start_move = 1
def flip_colour(c):
  if c == 'b':
    return 'w'
  else:
    return 'b'
  
adjusted_komi = 9.5
top_card = 20.0
for node in game.get_main_sequence()[start_move:]:
  p.stdin.write(bytes("komi " + str(adjusted_komi) + '\n', "utf-8"))
  p.stdin.write(b'genmove_debug b\n')
  p.stdin.write(b'undo\n')
  p.stdin.write(b'genmove_debug w\n')
  p.stdin.write(b'undo\n')
  next_move = node.get_move()
  if next_move[1] is not None:
    p.stdin.write(bytes(move_to_gtp(next_move) + '\n', "utf-8"))
  else: # pass means that someone took a card, need to change the komi
    sign = 1 if next_move[0] == "w" else -1
    adjusted_komi = adjusted_komi + top_card*sign
    top_card = top_card - 0.5
    

p.communicate() # This will end the KataGo process

tempfile = open(temp_filename, "r")
outfile = open(output_filename, "w")
outfile.write("move_num,game_move,card_temperature,")
outfile.write("black_move,black_score,white_move,white_score,temperature\n")

move_num = 1
card_temperature = 20.0
analyse_for = 'b'
line = tempfile.readline()
finished = False
while not finished:
  while not line.startswith("Tree"):
    line = tempfile.readline()
    if not line: # reached end of file
      finished = True
      break
  line = tempfile.readline() # Get the next line
  # line now looks something like this:
  # : T  12.02c W  11.56c S   0.46c ( +1.5) N     789  --  D16 C17 D17 C16 C14 C15 D15
  # and then two lines later there's a line starting with KataGo's best move.
  # nb the score is something like ( +1.5) or (+23.0)
  # There may or may not be a space after the (
  # 
  score_string = re.search("\(.*\)",line).group()
  score = float(score_string[1:-1]) # remove first and last characters and convert to number
  line = tempfile.readline() # This looks something like "---Black---", skip it
  line = tempfile.readline()
  kata_move = line.split()[0]
  if analyse_for == 'b':
    black_score = score
    black_move = kata_move
  else:
    white_score = score
    white_move = kata_move
    game_move = text_of_move_num(move_num)
    if game_move == "pass":
      card_temperature -= 0.5
    outfile.write(str(move_num)+","+game_move+",")
    outfile.write(str(card_temperature)+",")
    outfile.write(black_move+","+str(black_score)+",")
    outfile.write(white_move+","+str(white_score)+",")
    # Temperature is *difference* between black and white score,
    # but remember that score is from perspective of side to play
    # so we should *add* the numbers!
    current_temp  = white_score+black_score
    outfile.write(str(current_temp) + "\n")
    move_num += 1

  analyse_for = flip_colour(analyse_for)
  if move_num > game_length:
    finished = True

tempfile.close()
outfile.close()

df = pandas.read_csv(output_filename, index_col=0)
# In case you're wondering why create the CSV, load it into pandas, and later save it again,
# it's because I wrote v1 without pandas,
# and now doing it this way is less effort for me than refactoring.

df["adjusted_temperature"] = df["temperature"]
for i in range(1, len(df)): # this omits the last row, which is what we want!
  curr_temp = df.loc[i, "temperature"]
  next_temp = df.loc[i+1, "temperature"]
  if next_temp < curr_temp:
    df.loc[i, "adjusted_temperature"] = (curr_temp + next_temp)/2

# Game temperature is minimum of all temperatures seen so far,
# i.e. cumulative min
df["game_temperature"] = df["adjusted_temperature"].cummin()

df = df.rename(columns={"temperature": "raw_temperature"})

plt.figure(figsize=(12,6), dpi=80) # nb size is in inches not pixels!

axes = plt.gca()
df.plot(kind="line",  y="raw_temperature", linewidth=0.25, ax=axes)
df.plot(kind="line",  y="adjusted_temperature", color="black", linewidth=0.5, ax=axes)
df.plot(kind="line", y="game_temperature", color="green", ax=axes)
df.plot(kind="line", y="card_temperature", color="purple", linestyle = "dashed", ax=axes)
axis = plt.axis() # tuple of (xmin, xmax, ymin, ymax)
if axis[2] > 0: # make sure the y-axis always starts at zero
  axis = (axis[0], axis[1], 0, axis[3])
  plt.axis(axis)
axes.xaxis.set_minor_locator(MultipleLocator(10))
axes.yaxis.set_minor_locator(MultipleLocator(10))
axes.grid(which="minor", linestyle="dotted")
axes.grid(linestyle="dotted")
  
plt.savefig(image_filename)
df.to_csv(output_filename, index=False)

#os.remove(temp_filename)

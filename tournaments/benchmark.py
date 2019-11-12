from __future__ import print_function

# Run a self-play game with debug output,
# then use the output to count nodes/visits/playouts per second.
# Record the results in a CSV file together with time stamp and driver version.
# I want to check if a driver upgrade changes the speed of any programs!

# Separate formats needed for:
#   Leela and Leela Zero (same as each other)
#   Ray
#   Oakfoam
#   DreamGo

# Usage:
#   python benchmark.py engine time
# Output always appended to file benchmarks.csv

import sys, os, datetime, string, subprocess

def make_timestamp():
  return str(datetime.datetime.now())[0:16].replace(' ', '_').replace(':','-')

def driver_version():
  return subprocess.check_output("nvidia-smi", shell=True)\
    .split('\n')[2].split()[5]

def get_command(progname):
  filename = "command_lines/"+progname
  if (os.path.exists(filename)):
    command = tuple(open(filename, 'r'))[1]
  else:
    sys.exit("No command line found for program "+progname)
  command = command.replace('Command: ', '')
  command = command.replace('\n', '')
  return(command)

def make_command_line(prog1, prog2, time_limit):
  return('gogui -size 19 -program "gogui-twogtp -white \\"' +
       get_command(prog1) + '\\" -black \\"' + get_command(prog2) +
       '\\" -time ' + time_limit + ' -komi 7.5 -games 1 -debugtocomment -verbose -sgffile bench" ' +
       '-computer-both -auto'
       )

def parse_sgf(filename, mode):
  # Search filename, find all comments, strip out the counts of nodes etc according to the chosen mode (i.e. which engine created the comments)
  visits = 0
  nodes = 0
  playouts = 0
  sgftext = tuple(open(filename, 'r'))
  for l in sgftext:
    if mode=="LZ":
      if "visits" in l and "nodes" in l and "playouts" in l:
        visits += int(l.split()[0])
	nodes += int(l.split()[2])
	playouts += int(l.split()[4])
    elif mode=="ray":
      if "All Playouts" in l:
        playouts += int(l.split()[3])
    elif mode=="oakfoam":
      if "plts:" in l:
        playoutstring = l.split()[4] # nb this is "plts:nnnn" where nnnn is the number
	playouts += int(playoutstring[5:])
    elif mode=="dream":
      if "Nodes" in l:
	nodestring = l.split()[1] # nb this is a number followed by a comma
	nodes += int(nodestring[:-1])
    else:
      sys.exit("Error: unknown mode " + mode)
  return([visits, nodes, playouts])
  
def get_seconds(filename):
  resultline = tuple(open(filename, 'r'))[-1]
  blacktime = float(resultline.split('\t')[7])
  whitetime = float(resultline.split('\t')[8])
  return(blacktime + whitetime)

if (len(sys.argv) != 3):
  sys.exit("Usage: python benchmark.py engine time")
engine_name = sys.argv[1]
time_limit = sys.argv[2]

mode_string = engine_name.split("_")[0]
if mode_string in ["LZ", "LM", "leela"]:
  mode = "LZ"
elif mode_string in ["ray", "dream", "oakfoam"]:
  mode = mode_string
else:
  sys.exit("Don't know how to parse output for engine "+engine_name)

#print("Driver version: " + driver_version())
#print("Mode: " + mode)
#print(make_timestamp())

#print("\nCommand line to be executed:\n\n")
#print(make_command_line(engine_name, engine_name, time_limit))

#print("playtest.sgf-0.sgf used " + str(get_seconds("playtest.sgf.dat")) + " seconds.")
#print("\n\nTesting parsing of file.\n\n")
#print(parse_sgf("benchmark-LZ141-ray173.sgf", "LZ"))
#print(parse_sgf("benchmark-LZ141-ray173.sgf", "ray"))
#print(parse_sgf("benchmark-leela-dream.sgf", "LZ"))
#print(parse_sgf("benchmark-leela-dream.sgf", "dream"))
#print(parse_sgf("playtest.sgf-0.sgf", "oakfoam"))


# os.system(make_command_line(prog, prog)
os.system(make_command_line(engine_name, engine_name, time_limit))
time_taken = get_seconds("bench.dat")
stats = [x/time_taken for x in parse_sgf("bench-0.sgf", mode)]
output = [make_timestamp(), driver_version(), engine_name, str(time_taken)] + \
           [str(x) for x in stats]
outfile = open("benchmarks.csv", "a")
outfile.write(string.join(output, ","))
outfile.write("\n")
outfile.close()
os.remove("bench-0.sgf")
os.remove("bench.dat")

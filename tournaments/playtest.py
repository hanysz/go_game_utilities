# Test two engines by playing with gogui, displayed on screen,
# results not stored

import os, sys

verbose=False # if true, then engine output will be included in SGF file comments,
              # which leads to some massive SGF files
verbose=True

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
    return('gogui -size 19 -program "gogui-twogtp -white \\"' +
         get_command(prog1) + '\\" -black \\"' + get_command(prog2) +
         '\\" -time ' + time_limit + ' -komi 7.5 -games 1 -debugtocomment -verbose -sgffile playtest.sgf" ' +
	 '-computer-both -auto'
	 )
  else:
    return('gogui -size 19 -program "gogui-twogtp -white \\"' +
         get_command(prog1) + '\\" -black \\"' + get_command(prog2) +
         '\\" -time ' + time_limit + ' -komi 7.5 -games 1 -verbose -sgffile playtest.sgf" ' +
	 '-computer-both -auto'
	 )

if (len(sys.argv) != 4):
  sys.exit("Usage: python playtest.py player1 player2 time")

if os.path.exists("playtest.dat"):
  sys.exit("Error: file playtest.dat already exists.")

prog1 = sys.argv[1]
prog2 = sys.argv[2]
time_limit = sys.argv[3]

command_line = make_command_line(prog1, prog2)
print("Executing command:")
print("\n  "+command_line)
os.system(command_line)

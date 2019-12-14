#!/usr/bin/python3

# Copy one or more games from my GoGoD directory to the current directory.
# This is slightly tricky because it involves looking up which subfolder each game is in!

# Quick and dirty version of script, hardly any error checking!

# Edid the "GoGod dir = ..." line as appropriate for your system.

import sys, os, shutil
GoGoD_dir = "/sgf/GoGoD-2019-winter"

if (len(sys.argv) < 2 ):
  sys.exit("Usage: python extract_gogod.py game1 ...")


GoGoD_subdirs = [s for s in os.listdir(GoGoD_dir) if s[0].isdigit()]
GoGoD_subdirs.sort()
year_list = [int(s[:4]) for s in GoGoD_subdirs]

def fetch_game(g):
  g = g + ".sgf"
  if (os.path.exists(g)):
    print("Error: file " + g + " is already in the current directory")
    return
  year = g[:4]
  # Desired subfolder is the last one with start year <= game year
  folder_index = [y <= int(year) for y in year_list].index(False) - 1
  pathname = GoGoD_dir + "/" + GoGoD_subdirs[folder_index] + "/" + g
  shutil.copy2(pathname, g)
  print("Copied " + pathname)

for g in sys.argv[1:]:
  fetch_game(g)




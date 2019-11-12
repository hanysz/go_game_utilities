# Let's see if Python can run the BayesElo program and capture the ratings
# Command line arguments:
#   name of directory containing pgn files and total_crosstable.csv
#   filename for CSV output

import sys, os, pandas, subprocess, StringIO

if (len(sys.argv) != 3):
  sys.exit("Usage: python generate_ratings.py results_dir output.csv")
results_dir = sys.argv[1]
outfile = sys.argv[2]

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
  df.columns=["Name", "Elo", "Elo-", "Elo+", "games", "score", "avg_opp", "draws"]
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


#df = get_ratings(results_dir)
#df = get_anchored_ratings(results_dir, 'gnugo', 1500)
df = get_anchored_ratings(results_dir, 'pachi_nn', 2400)
playernames = df['Name'].tolist()

# Memo: to set index, use something like df.set_index('Name', inplace=True)

# Now let's get the total crosstable and merge on the ratings
df2 = pandas.read_csv(results_dir+"/total_crosstable.csv")

# Replace any blank cells by zeros:
df2.fillna(0, inplace=True)

# The first column of df2 must be called "Name" so we can merge with df1
df2.columns=["Name"] + df2.columns.tolist()[1:]

# Set an index for df2 so that we can easily look things up (wins/losses below)
df2.set_index('Name', inplace=True)


# Create df2a which is the same data as df2 but formatted differently
# Want to get the crosstable into "k/n" form (e.g. 5/7, played 7 won 5)
df2a = pandas.DataFrame("", index=playernames, columns=['Name'] + playernames)
df2a['Name']=playernames
for p1 in playernames:
  for p2 in playernames:
    if p1==p2:
      score="-"
    else:
      wins = int(df2.loc[p1][p2])
      losses = int(df2.loc[p2][p1])
      if wins+losses==0:
        score="-"
      else:
        score = str(wins) + "/" + str(wins+losses)
    df2a.loc[p1][p2]=score


df3 = pandas.merge(df, df2a, on="Name", how='outer')
df3.to_csv(outfile, index=False)
subprocess.Popen(["libreoffice --calc --nologo " + outfile], shell=True)

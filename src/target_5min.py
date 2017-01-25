import pandas as pd
import numpy as np
import sys
import os
import csv

__author__ = "Michael Girardot"
__project__ = "StarCraft 2 replay parser"


if __name__ == '__main__':
    e = 0
    p1_win_game = []
    directory = sys.argv[1]
    target = sys.argv[2]
    for fileName in os.listdir(directory):
        print ("Processing %s" % fileName)
        inputFile = os.path.join(directory, fileName)
        data = pd.read_csv(inputFile,
                                skiprows=2,
                                delimiter='\t',
                                #engine='python',
                                header=None,
                                names=["frames", "player", "action"],
                                error_bad_lines=False)
        players = list(set(data.iloc[:, 1]))
        #print("Player 1 : %s" % players[0])
        #print("Palyer 2 : %s" % players[1])

        if (len(players)==2):
            #print ("process file...")
            try:
                if max(data.frames[-1:] * 11.278/1000 >= 300):
                    p1 = data.loc[data['player'] == players[0]]
                    p2 = data.loc[data['player'] == players[1]]
                    p1_win_game.append(np.sum(p2['action'].str.find('Leave game') == 0))
                else:
                    print ("Game length shorter than 5 min")
            except:
                e += 1
                print ("Error in %s" % fileName)
                print ("Number of error files: %d" % e)
                pass
        else:
            print ("Not a 1v1 game...")
    #print p1_win_game
    with open(target, 'wb') as myfile:
        wr = csv.writer(myfile)
        wr.writerow(p1_win_game)

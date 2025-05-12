

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tankgame')))

from tankgame.tankgame import TankGame

def main():
    game = TankGame()
    game.run()

if __name__ == "__main__":
    main()
from hlt import *
from networking import *

from keras.models import Sequential
from keras.layers import Dense, Activation
from keras.optimizers import SGD, Adam, RMSprop

from os import listdir, remove
from os.path import join, isfile
import json

def loadGame(filename):
    # def stringUntil(gameFile, endChar):
    #     returnString = ""
    #     byte = gameFile.read(1)
    #     while byte != endChar.encode("utf-8"):
    #         returnString += byte.decode("utf-8")
    #         byte = gameFile.read(1)
    #     return returnString

    with open(filename) as data_file:
        gameData = json.load(data_file)

    botID = None
    botName = 'djma v3'
    frames = gameData['frames']
    moves = gameData['moves']
    width = gameData['width']
    height = gameData['height']
    productions = gameData['productions']
    numPlayers = gameData['num_players']

    try:
        # stringUntil(gameFile, "\n")

        # Get metadata
        # metadata = stringUntil(gameFile, "\n")

        # components = metadata.split(" ")
        # numFrames = len(gameData['frames'])

        # Get matt's playerID
        if gameData['player_names'].index('djma v3'):
                botID = gameData['player_names'].index(botName) + 1
                print("Found player ID: " + botID + " (" + botName + ")")
        else:
            print("Unable to find player")

        # Get production
        # productions = gameData['productions']

        # # Get the frames and moves
        # for frameIndex in range(numFrames-1):
        #     # Frames
        #     frames.append(GameMap(width=width, height=height, numberOfPlayers=numPlayers))
        #     x = 0
        #     y = 0
        #     while y < height:
        #         numTiles = int.from_bytes(gameFile.read(1), byteorder='big')
        #         ownerID = int.from_bytes(gameFile.read(1), byteorder='big')
        #
        #         strengths = []
        #         for a in range(numTiles):
        #             frames[-1].contents[y][x] = Site(ownerID, int.from_bytes(gameFile.read(1), byteorder='big'), productions[y*width + x])
        #
        #             x += 1
        #             if x == width:
        #                 x = 0
        #                 y += 1
        #                 if y == height:
        #                     break
        #     # Moves
        #     moves.append({(index % width, math.floor(index/width)):int.from_bytes(gameFile.read(1), byteorder='big') for index in range(width*height)})

    return botID, frames, moves, productions, width, height, numPlayers

def getNNData():
    inputs = []
    correctOutputs = []

    gamePath = "replays"

    for filename in [f for f in listdir(gamePath) if isfile(join(gamePath, f))]:
        print("Loading " + filename)

        botID, frames, moves, productions, width, height, numPlayers = loadGame(join(gamePath, filename))
        maxProduction = 0

        for y in range(height):
            for x in range(width):
                prod = productions[y][x]
                if prod > maxProduction:
                    maxProduction = prod

        print("Game max production: " + maxProduction)
        print("Processing frames...")
        for turnIndex in range(len(moves)):
            print(turnIndex + " ", end="")
            gameMap = GameMap(width, height, numPlayers)
            gameMap.contents = frames[turnIndex]

            # Load productions into gameMap
            for y in range(height):
                for x in range(width):
                    gameMap.getSite(Location(x,y)).append(productions[y][x])

            for y in range(height):
                for x in range(width):
                    loc = Location(x, y)
                    if gameMap.getSite(loc)[0] == botID:
                        box = [
                               gameMap.getSite(gameMap.getLocation(loc, NORTH), WEST),
                               gameMap.getSite(loc, NORTH),
                               gameMap.getSite(gameMap.getLocation(loc, NORTH), EAST),
                               gameMap.getSite(loc, EAST),
                               gameMap.getSite(gameMap.getLocation(loc, SOUTH), EAST),
                               gameMap.getSite(loc, SOUTH),
                               gameMap.getSite(gameMap.getLocation(loc, SOUTH), WEST),
                               gameMap.getSite(loc, WEST)
                        ]
                        nnInput = []
                        for site in box:
                            nnInput += [1 if site[0] == botID else -1, float(site[1] / 255), float(site[2] / maxProduction)]
                        inputs.append(nnInput)
                        correctOutputs.append([1 if a == moves[turnIndex][(x, y)] else 0 for a in range(5)])
    return inputs, correctOutputs

def trainModel():
    inputs, correctOutputs = getNNData()

    print("Collected data")

    trainingInputs = inputs[:len(inputs)//2]
    trainingOutputs = correctOutputs[:len(correctOutputs)//2]

    testInputs = inputs[len(inputs)//2:]
    testOutputs = correctOutputs[len(correctOutputs)//2:]

    model = Sequential()
    model.add(Dense(24, input_shape=(24, )))
    model.add(Activation('tanh'))
    model.add(Dense(24))
    model.add(Activation('tanh'))
    model.add(Dense(5))
    model.add(Activation('softmax'))

    model.summary()

    model.compile(loss='mean_squared_error', optimizer=SGD(lr=0.1, decay=1e-6, momentum=0.9, nesterov=True))

    model.fit(trainingInputs, trainingOutputs, validation_data=(testInputs, testOutputs))
    score = model.evaluate(testInputs, testOutputs, verbose=0)
    print(score)

    json_string = model.to_json()
    open('my_model_architecture.json', 'w').write(json_string)
    model.save_weights('my_model_weights.h5', overwrite=True)

trainModel()

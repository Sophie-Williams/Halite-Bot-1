from hlt import *
from networking import *
import logging
from operator import *
from random import *

myID, gameMap = getInit()
# logging.basicConfig(filename='last.log', level=logging.INFO, filemode="w")

DIRECTIONS = [NORTH, EAST, SOUTH, WEST]
def getClosestMine(a, b, mines):
    highProducationDistances = {}
    for (x, y) in mines:
        distance = gameMap.getDistance(Location(a, b), Location(x, y))
        highProducationDistances[(x, y)] = distance

    closestMine = min(highProducationDistances, key=highProducationDistances.get)
    return closestMine

def getDirection(radians, away):
    if radians == abs(math.pi):
        if away == 0:
            return [WEST]
        else:
            return [EAST]
    if radians > -math.pi and radians < -math.pi/2:
        if away == 0:
            return [NORTH, WEST]
        else:
            return [SOUTH, EAST]
    if radians == -math.pi/2:
        if away == 0:
            return [NORTH]
        else:
            return [SOUTH]
    if radians > -math.pi/2 and radians < 0:
        if away == 0:
            return [NORTH, EAST]
        else:
            return [SOUTH, WEST]
    if radians == 0:
        if away == 0:
            return [EAST]
        else:
            return [WEST]
    if radians > 0 and radians < math.pi/2:
        if away == 0:
            return [SOUTH, EAST]
        else:
            return [NORTH, WEST]
    if radians == math.pi/2:
        if away == 0:
            return [SOUTH]
        else:
            return [NORTH]
    if radians > math.pi/2 and radians < math.pi:
        if away == 0:
            return [SOUTH, WEST]
        else:
            return [NORTH, EAST]

mapDict = {}
for y in range(gameMap.height):
    for x in range(gameMap.width):
        site = gameMap.getSite(Location(x, y))
        mapDict[(x, y)] = (site.owner, site.strength, site.production)
groundZero = {(x, y) for ((x, y),(o, s, p)) in mapDict.items() if o == myID}
groundZero = list(groundZero)[0]
productionScale = 3
fastMode = False

# Find closest high Production zone
unownedTerritory = {(x, y): p for ((x, y),(o, s, p)) in mapDict.items() if o == 0}
highestProductionSites = sorted(unownedTerritory.items(), key=itemgetter(1), reverse=True)
highestP = highestProductionSites[0][1]
highestProductionCoords = [(x, y) for ((x, y), p) in highestProductionSites if p == highestP]

highProducationDistances = {}
for (x, y) in highestProductionCoords:
    distance = gameMap.getDistance(Location(x, y), Location(groundZero[0], groundZero[1]))
    highProducationDistances[(x, y)] = distance

closestMine = getClosestMine(groundZero[0], groundZero[1], highestProductionCoords)
# logging.info("Closest Mine: {}".format(closestMine))
sendInit("acheungBot")

while True:
    moves = []
    gameMap = getFrame()
    # Build Dict of current gameMap with all stats
    for y in range(gameMap.height):
        for x in range(gameMap.width):
            site = gameMap.getSite(Location(x, y))
            mapDict[(x, y)] = (site.owner, site.strength, site.production)
    myPieces = {(x, y):(o, s, p) for ((x, y),(o, s, p)) in mapDict.items() if o == myID}
    opponentPieces = {(x, y):(o, s, p) for ((x, y),(o, s, p)) in mapDict.items() if o != myID and o != 0}
    unownedPieces = {(x, y) for ((x, y),(o, s, p)) in mapDict.items() if o == 0}
    ownedMines = [(x, y) for ((x, y),(o, s, p)) in myPieces.items() if (x, y) in highestProductionCoords]
    unownedMines = set(highestProductionCoords) - set(ownedMines)

    territorySize = len(myPieces)
    opponentTerritorySize = len(opponentPieces)
    if territorySize > 550:
        fastMode = True
        productionScale = 5

    for key,value in myPieces.items():
        x, y = key[0], key[1]
        movedPiece = False

        # Grab nearby sites
        # Create two sets to prefer unoccupied space first
        ownedSites, unownedSites = [], []
        currentSite = gameMap.getSite(Location(x, y))

        # Make sure we have strength on the block
        if currentSite.strength < currentSite.production * productionScale:
            # moves.append(Move(Location(x, y), STILL))
            continue

        if not fastMode:

            for direction in DIRECTIONS:
                site = gameMap.getSite(Location(x, y), direction)
                if site.owner == myID:
                    ownedSites.append((site.strength, direction))
                else:
                    unownedSites.append((site.strength, direction))

            # TODO: Let's style on em. If the game map is >=40 and we have 3x the strength of the rest
            #       then we will grow a Two Sigma logo at ground zero

            # Prefer obtaining more territory
            if not movedPiece and unownedSites:
                minStrengthSite = min(unownedSites, key=itemgetter(0))
                lowestStrength = minStrengthSite[0]
                if currentSite.strength < lowestStrength:
                    # moves.append(Move(Location(x, y), STILL))
                    continue
                else:
                    # Move to takeover lowest strength local site
                    moves.append(Move(Location(x, y), minStrengthSite[1]))
                    continue

            # If there are no unowned territories, migrate towards high Production, then the nearest enemy
            if not movedPiece:
                if unownedMines:
                    closestMine = getClosestMine(x, y, unownedMines)
                    mineAngle = gameMap.getAngle(Location(x, y), Location(closestMine[0], closestMine[1]))
                    mineDirection = getDirection(mineAngle, 0)
                    
                    if len(mineDirection) > 1:
                        # If we're at an off angle, check two neighboring sites to lose the least amount of strength
                        if not movedPiece and gameMap.getSite(Location(x, y), mineDirection[0]).owner != myID:
                            moves.append(Move(Location(x, y), mineDirection[0]))
                            continue
                        if not movedPiece and gameMap.getSite(Location(x, y), mineDirection[1]).owner != myID:
                            moves.append(Move(Location(x, y), mineDirection[1]))
                            continue
                        else:
                            moves.append(Move(Location(x, y), mineDirection[randrange(0, 2)]))
                            continue
                    else:
                        moves.append(Move(Location(x, y), mineDirection[0]))
                        continue

                # Calculate all distances to enemy pieces
                opponentLocDistances = {}
                for key, value in opponentPieces.items():
                    distance = gameMap.getDistance(Location(x, y), Location(key[0], key[1]))
                    opponentLocDistances[(key[0], key[1])] = distance

                # Find the minimum distance
                closestEnemy = min(opponentLocDistances, key=opponentLocDistances.get)
                # logging.info("Closest enemy: {}".format(closestEnemy))

                # Get angle to that closest enemy
                enemyAngle = gameMap.getAngle(Location(x, y), Location(closestEnemy[0], closestEnemy[1]))
                # logging.info("Enemy angle: {}".format(enemyAngle))

                # Decide a direction to get there
                enemyDirection = getDirection(enemyAngle, 0)
                if len(enemyDirection) > 1:
                    # If we're at an off angle, check two neighboring sites to lose the least amount of strength
                    if not movedPiece and gameMap.getSite(Location(x, y), enemyDirection[0]).owner != myID:
                        moves.append(Move(Location(x, y), enemyDirection[0]))
                        continue
                    if not movedPiece and gameMap.getSite(Location(x, y), enemyDirection[1]).owner != myID:
                        moves.append(Move(Location(x, y), enemyDirection[1]))
                        continue
                    else:
                        moves.append(Move(Location(x, y), enemyDirection[randrange(0, 2)]))
                        continue
                else:
                    moves.append(Move(Location(x, y), enemyDirection[0]))
                    continue

        # If somehow we didn't account for an instruction, move the piece away from groundZero
        if not movedPiece:
            if unownedPieces:
                closestEmptyPiece = getClosestMine(x, y, unownedPieces)
                emptyAngle = gameMap.getAngle(Location(x, y), Location(closestEmptyPiece[0], closestEmptyPiece[1]))
                emptyDirection = getDirection(emptyAngle, 0)
                
                if len(emptyDirection) > 1:
                    # If we're at an off angle, check two neighboring sites to lose the least amount of strength
                    if not movedPiece and gameMap.getSite(Location(x, y), emptyDirection[0]).owner != myID:
                        moves.append(Move(Location(x, y), emptyDirection[0]))
                        continue
                    if not movedPiece and gameMap.getSite(Location(x, y), emptyDirection[1]).owner != myID:
                        moves.append(Move(Location(x, y), emptyDirection[1]))
                        continue
                    else:
                        moves.append(Move(Location(x, y), emptyDirection[randrange(0, 2)]))
                        continue
                else:
                    moves.append(Move(Location(x, y), emptyDirection[0]))
                    continue
                    
    sendFrame(moves)

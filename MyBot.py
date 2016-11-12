from hlt import *
from networking import *
import logging
from operator import *
from random import *
import signal

myID, gameMap = getInit()
#logging.basicConfig(filename='last.log', level=logging.INFO, filemode="w")

DIRECTIONS = [NORTH, EAST, SOUTH, WEST]
width = gameMap.width
height = gameMap.height
mapDict = {}
for y in range(gameMap.height):
    for x in range(gameMap.width):
        site = gameMap.getSite(Location(x, y))
        mapDict[(x, y)] = (site.owner, site.strength, site.production)
groundZero = {(x, y) for ((x, y), (o, s, p)) in mapDict.items() if o == myID}
groundZero = list(groundZero)[0]
productionScale = 3
fastMode = False


def signal_handler(signum, frame):
    raise Exception("timeout")

signal.signal(signal.SIGALRM, signal_handler)


def getSite(l, direction=STILL):
    l = getLocation(l, direction)
    return mapDict[(l.x, l.y)]


def getLocation(loc, direction):
    l = loc
    if direction != STILL:
        if direction == NORTH:
            if l.y == 0:
                l.y = height - 1
            else:
                l.y -= 1
        elif direction == EAST:
            if l.x == width - 1:
                l.x = 0
            else:
                l.x += 1
        elif direction == SOUTH:
            if l.y == height - 1:
                l.y = 0
            else:
                l.y += 1
        elif direction == WEST:
            if l.x == 0:
                l.x = width - 1
            else:
                l.x -= 1
    return l


def getDistance(l1, l2):
    dx = abs(l1.x - l2.x)
    dy = abs(l1.y - l2.y)
    if dx > width / 2:
        dx = width - dx
    if dy > height / 2:
        dy = height - dy
    return dx + dy


def getClosestMine(a, b, mines):
    highProducationDistances = {}
    for (x, y) in mines:
        distance = getDistance(Location(a, b), Location(x, y))
        highProducationDistances[(x, y)] = distance

    closestMine = min(highProducationDistances, key=highProducationDistances.get)
    return closestMine


def getDirection(radians, away):
    if radians == abs(math.pi):
        if away == 0:
            return [WEST]
        else:
            return [EAST]
    if radians > -math.pi and radians < -math.pi / 2:
        if away == 0:
            return [NORTH, WEST]
        else:
            return [SOUTH, EAST]
    if radians == -math.pi / 2:
        if away == 0:
            return [NORTH]
        else:
            return [SOUTH]
    if radians > -math.pi / 2 and radians < 0:
        if away == 0:
            return [NORTH, EAST]
        else:
            return [SOUTH, WEST]
    if radians == 0:
        if away == 0:
            return [EAST]
        else:
            return [WEST]
    if radians > 0 and radians < math.pi / 2:
        if away == 0:
            return [SOUTH, EAST]
        else:
            return [NORTH, WEST]
    if radians == math.pi / 2:
        if away == 0:
            return [SOUTH]
        else:
            return [NORTH]
    if radians > math.pi / 2 and radians < math.pi:
        if away == 0:
            return [SOUTH, WEST]
        else:
            return [NORTH, EAST]


# Find closest high Production zone
unownedTerritory = {(x, y): p for ((x, y), (o, s, p)) in mapDict.items() if o == 0}
highestProductionSites = sorted(unownedTerritory.items(), key=itemgetter(1), reverse=True)
highestP = highestProductionSites[0][1]
highestProductionCoords = [(x, y) for ((x, y), p) in highestProductionSites if p == highestP]

highProducationDistances = {}
for (x, y) in highestProductionCoords:
    distance = getDistance(Location(x, y), Location(groundZero[0], groundZero[1]))
    highProducationDistances[(x, y)] = distance

closestMine = getClosestMine(groundZero[0], groundZero[1], highestProductionCoords)

sendInit("acheungBot")

while True:
    signal.setitimer(signal.ITIMER_REAL, .95)
    try:
        moves = []
        gameMap = getFrame()
        # Build Dict of current gameMap with all stats
        for y in range(gameMap.height):
            for x in range(gameMap.width):
                site = gameMap.getSite(Location(x, y))
                mapDict[(x, y)] = (site.owner, site.strength, site.production)

        # Divide mapDict into specific sets
        myPieces = {(x, y): (o, s, p) for ((x, y), (o, s, p)) in mapDict.items() if o == myID}
        opponentPieces = {(x, y): (o, s, p) for ((x, y), (o, s, p)) in mapDict.items() if o != myID and o != 0}
        unownedPieces = {(x, y) for ((x, y), (o, s, p)) in mapDict.items() if o == 0}
        ownedMines = [(x, y) for ((x, y), (o, s, p)) in myPieces.items() if (x, y) in highestProductionCoords]
        unownedMines = set(highestProductionCoords) - set(ownedMines)

        territorySize = len(myPieces)
        opponentTerritorySize = len(opponentPieces)
        if territorySize > 550:
            fastMode = True
            productionScale = 5

        for key, value in myPieces.items():
            x, y = key[0], key[1]
            # movedPiece = False

            # Grab nearby sites
            # Create two sets to prefer unoccupied space first
            ownedSites, unownedSites = [], []
            currentSite = getSite(Location(x, y))

            # Make sure we have strength on the block
            if currentSite[1] < currentSite[2] * productionScale:
                continue

            if not fastMode:

                for direction in DIRECTIONS:
                    site = getSite(Location(x, y), direction)
                    if site[0] == myID:
                        ownedSites.append((site[1], direction))
                    else:
                        unownedSites.append((site[1], direction))

                # TODO: Let's style on em. If the game map is >=40 and we have 3x the strength of the rest
                #       then we will grow a Two Sigma logo at ground zero

                # Prefer obtaining more territory
                if unownedSites:
                    minStrengthSite = min(unownedSites, key=itemgetter(0))
                    lowestStrength = minStrengthSite[0]
                    if currentSite[1] <= lowestStrength:
                        continue
                    else:
                        # Move to takeover lowest strength local site
                        moves.append(Move(Location(x, y), minStrengthSite[1]))
                        continue

                # If there are no unowned territories, migrate towards high Production, then the nearest enemy

                if unownedMines:
                    closestMine = getClosestMine(x, y, unownedMines)
                    mineAngle = gameMap.getAngle(Location(x, y), Location(closestMine[0], closestMine[1]))
                    mineDirection = getDirection(mineAngle, 0)

                    if len(mineDirection) > 1:
                        # If we're at an off angle, check two neighboring sites to lose the least amount of strength
                        #     if gameMap.getSite(Location(x, y), mineDirection[0]).owner != myID:
                        #         moves.append(Move(Location(x, y), mineDirection[0]))
                        #         continue
                        #     if gameMap.getSite(Location(x, y), mineDirection[1]).owner != myID:
                        #         moves.append(Move(Location(x, y), mineDirection[1]))
                        #         continue
                        #     else:
                        moves.append(Move(Location(x, y), mineDirection[randrange(0, 2)]))
                        continue
                    else:
                        moves.append(Move(Location(x, y), mineDirection[0]))
                        continue

                # Calculate all distances to enemy pieces
                opponentLocDistances = {}
                for key, value in opponentPieces.items():
                    distance = getDistance(Location(x, y), Location(key[0], key[1]))
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
                    # if not movedPiece and gameMap.getSite(Location(x, y), enemyDirection[0]).owner != myID:
                    #    moves.append(Move(Location(x, y), enemyDirection[0]))
                    #    continue
                    # if not movedPiece and gameMap.getSite(Location(x, y), enemyDirection[1]).owner != myID:
                    #    moves.append(Move(Location(x, y), enemyDirection[1]))
                    #    continue
                    # else:
                    moves.append(Move(Location(x, y), enemyDirection[randrange(0, 2)]))
                    continue
                else:
                    moves.append(Move(Location(x, y), enemyDirection[0]))
                    continue

            # If somehow we didn't account for an instruction, move the piece away toward empty pieces
            if unownedPieces:
                closestEmptyPiece = getClosestMine(x, y, unownedPieces)
                emptyAngle = gameMap.getAngle(Location(x, y), Location(closestEmptyPiece[0], closestEmptyPiece[1]))
                emptyDirection = getDirection(emptyAngle, 0)

                if len(emptyDirection) > 1:
                    # If we're at an off angle, check two neighboring sites to lose the least amount of strength
                    # if gameMap.getSite(Location(x, y), emptyDirection[0]).owner != myID:
                    #    moves.append(Move(Location(x, y), emptyDirection[0]))
                    #    continue
                    # if gameMap.getSite(Location(x, y), emptyDirection[1]).owner != myID:
                    #    moves.append(Move(Location(x, y), emptyDirection[1]))
                    #    continue
                    # else:
                    moves.append(Move(Location(x, y), emptyDirection[randrange(0, 2)]))
                    continue
                else:
                    moves.append(Move(Location(x, y), emptyDirection[0]))
                    continue

        sendFrame(moves)
    except Exception:
        #logging.info("Timing out...")
        sendFrame(moves)

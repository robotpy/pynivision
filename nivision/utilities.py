#
# Utilities functions
#
from . import core

def imaqMakePoint(xCoordinate, yCoordinate):
    return core.Point(xCoordinate, yCoordinate)

def imaqMakePointFloat(xCoordinate, yCoordinate):
    return core.PointFloat(xCoordinate, yCoordinate)

def imaqMakeRect(top, left, height, width):
    return core.Rect(top, left, height, width)

def imaqMakeRotatedRect(top, left, height, width, angle):
    return core.RotatedRect(top, left, height, width, angle)

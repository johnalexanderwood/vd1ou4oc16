from enum import Enum

# class WidgetType(Enum):
#     UNKNOWN = 00
#     LABEL = 10
#     SCALE = 20
#     BUTTON = 30
#     BUTTON_TOOL = 40
#     BUTTON_LAYOUT = 50
#     TOGGLE = 60
#     TREEVIEW = 70
#     SEPERATOR = 80
 
# # For just now we manually have to add to the state 
# # every time a new plugin is added
# class State():
#     EMPTY = 0
#     PAN_ZOOM = 1
#     MANUAL_DRAW = 2
#     SELECT_VALUE = 3
#     ONE_SCALE = 4
#     PLUGIN_TWO = 5
#     NEW_SELECT_VALUE = 6

class View(Enum):
    SINGLE = 0
    DOUBLE = 1
    MULTIPLE = 2


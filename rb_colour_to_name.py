import webcolors
import cv2
import numpy as np

# Next two functions derived from:
# https://stackoverflow.com/questions/9694165/convert-rgb-color-to-english-color-name-like-green-with-python
# Accessed: 28/04/2021
# Author: fraxel
# JW - Modified by me to only return one colour and to also accept HSV input values
def closest_colour(requested_colour):
    min_colours = {}
    for key, name in webcolors.CSS3_HEX_TO_NAMES.items():
        r_c, g_c, b_c = webcolors.hex_to_rgb(key)
        rd = (r_c - requested_colour[0]) ** 2
        gd = (g_c - requested_colour[1]) ** 2
        bd = (b_c - requested_colour[2]) ** 2
        min_colours[(rd + gd + bd)] = name
    return min_colours[min(min_colours.keys())]

def get_colour_name(requested_colour, hsv=True):
    if hsv:
        array = np.zeros((1, 1, 3), dtype=np.uint8)

        array[0, 0, 0] = requested_colour[0]
        array[0, 0, 1] = requested_colour[1]
        array[0, 0, 2] = requested_colour[2]

        result_hsv = cv2.cvtColor(array, cv2.COLOR_HSV2RGB)

        requested_colour = (result_hsv[0, 0, 0],
                            result_hsv[0, 0, 1],
                            result_hsv[0, 0, 2]
                            )
    try:
        closest_name = webcolors.rgb_to_name(requested_colour)
    except ValueError:
        closest_name = closest_colour(requested_colour)
        actual_name = None
    return closest_name

# Manual Test Code
# while True:
#     red = input('Enter value for H:')
#     green = input('Enter value for S:')
#     blue = input('Enter value for V:')
#     print("Closest colour name:", get_colour_name((int(red), int(green), int(blue))))
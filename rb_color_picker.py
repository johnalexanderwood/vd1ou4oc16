# Modified from: https://github.com/israel-dryer/Color-Wheel
# Author: Israel Dryer
# Accessed: 21 Jan 2024

# From Original:
# Title: Colorwheel Demonstration
# Description: This demonstrates the ability of creating a color wheel color select in Tkinter
# Author: Israel Dryer
# Modified: 2020-05-30

import math
import cv2
import numpy as np
import PIL
import ttkbootstrap as ttk
from ttkbootstrap.constants import *


class ColorPicker(ttk.Frame):
    def __init__(self, *args, size=170, show_selected=True, **kwargs):
        super().__init__(*args, **kwargs)

        self.wheel = ttk.PhotoImage(file='./resources/color_wheel_bgr.png')
        subsample = self.wheel.width() // size
        self.wheel = self.wheel.subsample(subsample, subsample)
        self.target = ttk.PhotoImage(file='./resources/target.png')

        self.show_selected = show_selected
        self.center = self.wheel.width()//2
        self.x = self.center
        self.y = self.center
        self.value_height = self.wheel.width() // 10
        self.values_pady = 4

        self.values = self.make_value_sweep()

        self.canvas = ttk.Canvas(
            self, 
            height=self.wheel.width() + self.value_height + self.values_pady, 
            width=self.wheel.width()
        )
        self.canvas.pack(side=ttk.TOP, fill=ttk.BOTH, expand=ttk.YES)

        if show_selected:
            # Make the label with adjusting colors (based on selection)
            self.color_label = ttk.StringVar()
            self.color_label.set('#FFFFFF'+ f"\nR:255 G:255 B:255")
            self.color_select = ttk.Label(
                self, 
                #justify=CENTER,
                textvariable=self.color_label,
                background='white', 
                #width=50, 
                #font=('Arial', 20, 'bold')
            )

        # Make the scale for value
        self.scale_value = ttk.Scale(
            self,
            orient=ttk.HORIZONTAL,
            command=self.event_colour_picker_change,
            from_=0,
            to=255,
        )
        self.scale_value.set(255)
        self.scale_value.pack(
            side=ttk.TOP, 
            fill=ttk.BOTH, 
            expand=ttk.YES, 
            ipady=4, 
            ipadx=1, 
            pady=4, 
            padx=12
        )

        # Make the scale for the threshold
        # self.scale_threshold = ttk.Scale(
        #     self,
        #     orient=ttk.HORIZONTAL,
        # )
        # self.scale_threshold.pack(
        #     side=ttk.TOP, 
        #     fill=ttk.BOTH, 
        #     expand=ttk.YES, 
        #     ipady=4, 
        #     ipadx=4, 
        #     pady=4, 
        #     padx=4
        # )

        if show_selected:
            self.color_select.pack(
                side=ttk.TOP, 
                fill=ttk.BOTH, 
                expand=ttk.YES, 
                pady=4,
                padx=4,
            )

        # Add in the pictures
        self.canvas.create_image(self.center, self.center, image=self.wheel)
        self.canvas.create_image(self.center, self.center, image=self.target)
        self.canvas.create_image(
            self.center, 
            self.wheel.height() + (self.value_height//2) + self.values_pady, 
            image=self.values
        )   

        # Bind the events once everything is in place
        self.canvas.bind("<B1-Motion>", self.event_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.event_mouse_click)

    def make_value_sweep(self, hue=255, saturation=0):
        hsv_value_sweep = np.zeros((self.value_height, 255, 3), dtype=np.uint8)
        hsv_value_sweep[:,:, 0:2] = (hue, saturation) 
        hsv_value_sweep[:,:,2] = np.linspace(0, 255, 255)
        value_sweep = cv2.cvtColor(hsv_value_sweep, cv2.COLOR_HSV2RGB)
        value_sweep = cv2.resize(value_sweep, (self.wheel.width()-28, self.value_height))
        values = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(value_sweep))
        return values

    def event_colour_picker_change(self, event=None):
        # limit coords
        if self.x >= self.wheel.width():
            self.x = self.wheel.width() - 1
        elif self.x < 0:
            self.x = 0
        
        if self.y >= self.wheel.height():
            self.y = self.wheel.height() - 1
        elif self.y < 0:
            self.y = 0

        # clear the canvas and redraw
        self.canvas.delete('all')
        self.canvas.create_image(self.center, self.center, image=self.wheel)
        self.canvas.create_image(self.x, self.y, image=self.target)
        
        # Get color
        hsv_color = np.array(self.get_hsv_colour(), dtype=np.uint8)

        # make value sweep above scale
        self.values = self.make_value_sweep(hsv_color[0], hsv_color[1])
        self.canvas.create_image(
            self.center, 
            self.wheel.width() + (self.value_height//2) + self.values_pady, 
            image=self.values
        ) 
            
        # need to get the value from scale value
        value = self.scale_value.get()
        hsv_color[2] = int(value)

        if self.show_selected:
            # format the rgb color in hexadecimal
            hsv_array = np.zeros((2,2,3), dtype=np.uint8)
            hsv_array[0,0] = hsv_color
            rgb_color = cv2.cvtColor(hsv_array, cv2.COLOR_HSV2RGB)
            hex_color = f"#{rgb_color[0,0,0]:02x}{rgb_color[0,0,1]:02x}{rgb_color[0,0,2]:02x}"
            hsv_color_str = f"\nH:{hsv_color[0]} S:{hsv_color[1]} V:{hsv_color[2]}"

            # adjust the label background color and text
            self.color_label.set(f"R:{rgb_color[0,0,0]} G:{rgb_color[0,0,1]} B:{rgb_color[0,0,2]} {hsv_color_str}")
            self.color_select['background'] = hex_color
            if hsv_color[2] > 170:
                self.color_select['foreground'] = 'black'
            else:
                self.color_select['foreground'] = 'lightgray'

    def event_mouse_drag(self, event):
        """Mouse movement callback"""
        # get mouse coordinates
        self.x = event.x
        self.y = event.y
        self.event_colour_picker_change()

    def event_mouse_click(self, event):
        """Mouse movement callback"""
        # get mouse coordinates
        self.x = event.x
        self.y = event.y
        self.event_colour_picker_change()

    def get_hsv_colour(self):
        # get rgb color from pixel location in image
        rgb_color = self.wheel.get(self.x, self.y)
        print(f'get_hsv_colour | rgb_color: {rgb_color}')
        rgb_array = np.zeros((2,2,3), dtype=np.uint8)
        rgb_array[:,:,:] = rgb_color
        #rgb_array[:,:,2] = int(self.scale_value.get())

        # make this hsv
        hsv_color = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2HSV)
        output = (
            hsv_color[0,0,0],
            hsv_color[0,0,1],
            int(self.scale_value.get()), 
        )

        #print(f'get_hsv_colour | rgb_color: {rgb_color} | hsv_color: {hsv_color} | rgb_array: {rgb_array}')
        return output

    def set_hsv_colour(self, color=(255, 255, 255)):
        r = color[1] * ((self.wheel.width()/2) / 255)
        theta = (color[0]*2) * math.pi/180
        self.x = int((self.wheel.width()/2) + (r * math.cos(theta)))
        self.y = int((self.wheel.height()/2) - (r * math.sin(theta)))

        if self.x >= self.wheel.width():
            self.x = self.wheel.width()-1
        if self.x < 0:
            self.x = 0
        
        if self.y >= self.wheel.height():
            self.y = self.wheel.height()-1
        if self.y < 0:
            self.y = 0

        self.scale_value.set(int(color[2]))


class App(ttk.Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.text = ttk.Scale(self)

        self.color_picker = ColorPicker(size=200)
        self.color_picker.pack(
            side=ttk.LEFT, 
            fill=ttk.BOTH, 
            expand=ttk.YES,
            ipadx=4,
            ipady=4,
            padx=4,
            pady=4,
        )

        self.color_picker.set_hsv_colour((90, 254, 255))
        
        print(self.color_picker.get_hsv_colour())


if __name__ == "__main__":
    root = ttk.Window(
        title='Colorwheel',
        iconphoto="./resources/logo_full_res.png",
        minsize=(10, 10),
        maxsize=(3500, 1400),
    )

    app = App(root)

    app.mainloop()
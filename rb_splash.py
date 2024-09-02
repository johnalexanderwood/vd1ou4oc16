""" This module contains the Splash Screen for the RockBase application."""

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.tooltip import ToolTip
import time
from PIL import ImageTk
from tkinter import PhotoImage

from pathlib import Path

PATH = Path(__file__).parent / 'resources'


class Splash:
    def __init__(self, disappear_automatically=True):
        splash = ttk.Window(
            title='RockBase',
            iconphoto="./resources/logo_full_res.png",
            minsize=(735, 500),
            maxsize=(735, 500),
        )
        splash.place_window_center()

        self.frame = ttk.Frame(splash, style=(DEFAULT))
        self.frame.pack(fill=BOTH, expand=YES, padx=10, pady=10)

        title_font_1 = ("Verdana", 48, )  # Changes font
        title_font_2 = ("Verdana", 24)  # Changes font
        normal_font = ("Verdana", 10)  # Changes font

        ttk.Label(self.frame, text='\nRockBase', font=title_font_1, bootstyle=(DEFAULT)).pack()
        ttk.Label(self.frame, text='version 4.1.0\n\n', font=normal_font, bootstyle=(DEFAULT)).pack()
        ttk.Label(self.frame, text='John Wood', font=normal_font, bootstyle=(DEFAULT)).pack()
        ttk.Label(self.frame, text='© 2020-2024\n\n', font=normal_font, bootstyle=(DEFAULT)).pack()
        
        splash.photoimage_icon = PhotoImage(master=splash, name="icon", file="./resources/logo_47_47.png")
        ttk.Label(self.frame, image=splash.photoimage_icon,).pack()

        ttk.Label(self.frame, text='\nFrom the RockFace Suite of Tools\n', bootstyle=(DEFAULT)).pack()
        ttk.Label(self.frame, text='VOG', font=title_font_2, bootstyle=(DEFAULT)).pack()
        ttk.Label(self.frame, text='www.virtualoutcrop.com', font=normal_font, bootstyle=(DEFAULT)).pack()

        splash.update()

        if disappear_automatically:
            time.sleep(2)
            splash.destroy()
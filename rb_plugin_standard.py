#from abc import ABC, abstractclassmethod
import copy
import cv2
#import rb_colour_to_name
#from enum import Enum
from functools import partial
import numpy as np
import PIL
import random
from tkinter import EventType
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.tooltip import ToolTip
#import time

from rb_types import *
#from rb_filters import Filters
from rb_plugin_base import Base
#from rb_color_picker import ColorPicker


# All plugin modules need to state order to display plugin Tool buttons on Tool menu
plugin_order = [
    'PanZoom',
    # 'DrawMask',
]


class PanZoom(Base):
    # Configuration
    type_view = True       # Only changes the view 
    type_solo = True

    def __init__(self, 
                 config=None,
                 id=None, 
                 text_name=None,
                 is_global=True, 
                 widgets=None, 
                 widget_parent=None, 
                 images=None,
                 event_scale_change=None,
                 event_checkbox_change=None):
        
        # Setup the values to create the plugin with
        self.default_params = {
            'Active': False,         # True, False - Needed for compatability
        }

        # The values that are changes as the user interacts with the plugin
        self.params = copy.copy(self.default_params)    
        self.value = None

        self.id = id
        self.text_name = text_name
        self.is_global = True

        self.event_checkbox_change = event_checkbox_change
        super().__init__(self.params)

    def make_button_tool(self, layout, tool_parent):
        # button_select_value
        name = 'button_pan_zoom'
        image = 'arrows_gray'
        text = "Pan and Zoom"
        value = "PanZoom"
        # print(layout.ui_images)
        layout.ui_images[image] = layout.ui_images_raw[image].resize((
            layout.config.button_tool_width, 
            layout.config.button_tool_height
        ))
        layout.ui_images[image] = PIL.ImageTk.PhotoImage(layout.ui_images[image])

        layout.widgets[name] = ttk.Button(
            tool_parent,
            text=text,
            command=partial(layout.event_button_tool, value),
            image=layout.ui_images[image],
            bootstyle=(SECONDARY),
        )

        layout.widgets[name].pack(
            layout.config.standard_button_tool
        )

        ToolTip(layout.widgets[name], text=text)

    def make_widgets(self):
        print('Start to make the widgets for the properties')

    def apply(self, mask):
        pass

    def delete_mask_or_interp(self):
        pass

    def mouse_select_value(self, event):
        self.value = self.images.screen_coords_to_hex(event.x, event.y)  
        self.widgets['label_select_value_scale'].config(text=self.value)
        print('mouse selected value', self.value) 

    # def self_mouse_motion(self, event, images, widgets):
    #     pass

    @staticmethod
    def mouse_motion(event, images, widgets):
        pass
    
    @staticmethod
    def get_cursor():
        # override cursor
        return 'fleur'
    
    def generate_id(self, config=None):
        return 'PanZoom'

    def generate_name_text(self, path=None):
        name = 'PanZoom'
        return name
    

 
from abc import ABC, abstractclassmethod
import copy
import cv2
import rb_colour_to_name
from enum import Enum
from functools import partial
import numpy as np
import PIL
import random
from tkinter import EventType
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.tooltip import ToolTip
import time

from rb_types import *
from rb_filters import Filters
from rb_plugin_base import Base
from rb_color_picker import ColorPicker


# All plugin modules need to state order to display plugin Tool buttons on Tool menu
plugin_order = [
    #'PanZoom',
    'DrawMask',
    'SelectValue',
    'FinalSmooth',
]


class DrawMask(Base):
    # Plugin Configuration
    type_needs_apply = False
    type_draw = True
    type_mask = True 
    type_solo = True
    type_local = True
    type_create_on_tool_button = True # Plugin instance is created when the tool is created
    type_has_popup = True

    def __init__(self, 
                 config=None,
                 id=None, 
                 text_name=None,
                 is_global=False,
                 widgets=None, 
                 widget_parent=None, 
                 images=None,
                 event_scale_change=None,
                 event_checkbox_change=None):
        
        # Setup the values to create the plugin with
        # TODO push defaults to config file
        self.default_params = {
            'Active': True,         # True, False
            'Remove': True,         # True Remove, False Keep
            'RGB': True,            # True over RGB images
            'Size': 48,             # 0:1 mapped to 0 - 255
            'RGBFile': "",      # The rgb image this drawn mask applies to
        }

        self.config = config
        self.id = id
        self.text_name = text_name
        self.is_global = is_global
        self.widgets = widgets
        self.widget_parent = widget_parent
        self.images = images
        # The values that are changes as the user interacts with the plugin
        self.params = copy.copy(self.default_params)    
        self.Type = DrawMask  

        # Keep  track of mouse state etc
        self.mouse = {
            'event': 0,
            'screen_x': 0, # screen_x - mouse does not know about zoom etc
            'screen_y': 0, # screen_y - mouse does not know about zoom etc
            'active': False,  # True is moving, dragging, any button down...
            'over_secondary': False,  # True if over the secondary image
            'flags': 0,
            'param': ''
        }

        super().__init__(self.params)

    def make_button_tool(self, layout, tool_parent):
        # button_select_value
        name = 'button_manual_draw'
        image = 'pencil_gray'
        text = "Draw Mask"
        value = "DrawMask"

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
        print('Start to make the widgets for the properties: Size, keep / remove')

        # Note: The Active checkbox is made by RockBase Class

        # Checkbutton keep
        self.widgets['checkbutton_manual_draw_keep'] = ttk.Checkbutton(
            self.widget_parent,
            text='Keep / Remove',
            bootstyle=(DEFAULT, TOGGLE, ROUND),
            command=partial(self.apply, True),
        )

        # TODO this should not be state but value? or something? fix
        # chk.state(['selected'])  # check the checkbox
        # chk.state(['!selected']) # clear the checkbox
        self.widgets['checkbutton_manual_draw_keep'].pack(
            side=TOP,
            ipadx=4,
            ipady=4,
            padx=1,
            pady=1,
        )

        if self.params['Remove']:
            self.widgets['checkbutton_manual_draw_keep'].state(['selected'])
        else:
            self.widgets['checkbutton_manual_draw_keep'].state(['!selected'])

        ToolTip(self.widgets['checkbutton_manual_draw_keep'], text="Keep if off. Remove if on.")       

        # Horizontal Separator
        name = 'separator_manual_draw_start'
        self.widgets[name] = ttk.Separator(
            self.widget_parent,
            orient=HORIZONTAL,
            bootstyle=(DEFAULT),
        )
        self.widgets[name].pack(
            side=TOP, 
            fill=X,
            #ipadx=4,
            ipady=4,
            #padx=1,
            pady=1,
        )

        # label Size
        self.widgets['label_manual_draw_size'] = ttk.Label(
            self.widget_parent,
            text='Size',
            state=ACTIVE,
            bootstyle=(DEFAULT,),
        )

        self.widgets['label_manual_draw_size'].pack(
            self.config.standard_label
        )

        # Scale Size
        self.widgets['scale_manual_draw_size'] = ttk.Scale(
            self.widget_parent,
            value=self.params['Size'],  
            state=ACTIVE,
            bootstyle=(DEFAULT,),
            from_= 0,
            to= 255,
            command=partial(self.apply, True),
        )

        self.widgets['scale_manual_draw_size'].pack(
            self.config.standard_scale
        )

        ToolTip(self.widgets['scale_manual_draw_size'], text="Change Drawing Size")

        # if we are making the widgets we are likely going to be drawing
        self.images.draw_circle_size = int(self.params['Size']) # drawing preview circle size

    def event_popup(self, event):
        print(f'event_popup | {event}')
        # Then in plugin create plugin and populate with all the rocktype / colors...
        self.widgets['popup_menu_view'].delete(0, 'end')
        self.widgets['popup_menu_view'].add_command(
            label='Keep', 
            command=partial(self.event_popup_select, remove=False)
        ) 
        self.widgets['popup_menu_view'].add_command(
            label='Remove', 
            command=partial(self.event_popup_select, remove=True)
        ) 

        try: 
            self.widgets['popup_menu_view'].tk_popup(event.x_root, event.y_root) 
        finally: 
            self.widgets['popup_menu_view'].grab_release() 

    def event_popup_select(self, remove):
        print(f'event_popup_select | remove {remove}')

        # Set the params
        self.params['Remove'] = remove

        # ALSO force update of the widgets
        self.widgets['checkbutton_manual_draw_keep'].set(remove)
        self.widgets['checkbutton_manual_draw_keep'].update()
  
    def apply(self, changed_params=True, over_secondary=False):
        if changed_params:
            # Get the values from the scales (change to right type and range done in convert fuction)
            remove = self.widgets['checkbutton_manual_draw_keep'].instate(['selected'])
            size = int(self.widgets['scale_manual_draw_size'].get())

            self.params.update({
                'Remove': remove,
                'Size': size,
                'RGB': not over_secondary,
            })
        else:
            # Note: RGB vs Dip can only be set on the initial mouse select
            #       IE not possible to update this after creation of plugin instance.
            self.params['RGB'] = not over_secondary

        # need to send back mask
        self.images.draw_circle_size = int(self.params['Size']) # drawing preview circle size
        self.mouse_draw_line(0, 0, 0, 0, size=0, remove=True)

    def delete_mask_or_interp(self):
        # TODO
        # make this work for multiple manual drawn masks
        # if a draw mask exists delete it
        result = self.images._inter_msk.get(self.id, False)
        if hasattr(result, 'shape'): # "Tes"t" if a numpy array
            del(self.images._inter_msk[self.id])

    def mouse_select_value(self, event, over_secondary):
        print('DrawMask:mouse_select_value', event) 

    def mouse_drawing(self, event):
        size = self.params['Size'] 
        remove = self.params['Remove']

        if event.type == EventType.ButtonPress and event.num == 1:
            # Draw line with current class
            self.mouse_draw_line(
                event.x, 
                event.y,
                self.mouse['screen_x'],
                self.mouse['screen_y'],
                size,
                remove,
            )
            self.mouse['active'] = True
        elif event.type == EventType.Motion and self.mouse['active'] is True:
            # Draw line with current class
            self.mouse_draw_line(
                event.x, 
                event.y,
                self.mouse['screen_x'],
                self.mouse['screen_y'],
                size,
                remove,
            )
        elif event.type == EventType.ButtonRelease and event.num == 1:
            # reset
            self.mouse['active'] = False

        # keep the x and y
        self.mouse['screen_x'] = event.x
        self.mouse['screen_y'] = event.y

    def mouse_draw_line(self, m_x, m_y, old_mouse_x, old_mouse_y, size, remove):
        """draw on the screen - continuous draw for now"""
        
        # Guard Clause: Check there are images loaded by looking at image_height
        if self.images.image_height is None:
            return
        
        # If there is no manual mask layer create it
        # TODO user the plugins id here.
        # Does the plugin know it own id at this point?
        if not self.id in self.images._inter_msk:
            self.images._inter_msk[self.id] = np.zeros((self.images.image_height, 
                                                            self.images.image_width), 
                                                            dtype=np.uint8)
            self.images._inter_msk[self.id][:,:] = self.config.blank_mask_colour

        if remove:
            colour = 255
        else:
            colour = 0

        # Correct the cursor size for the current matrix
        size = int(size / self.images.matrix[0, 0])
        if size <= 0:
            size = 1

        d_x, d_y = self.images.transform_view2buffer(old_mouse_x, old_mouse_y)
        new_d_x, new_d_y = self.images.transform_view2buffer(m_x, m_y)

        # Line needs to be more than one pixel long
        if new_d_x == d_x and new_d_y == d_y:
            new_d_x += random.choice([-1, 1])
            new_d_y += random.choice([-1, 1])

        # Draw the line on current zoom level
        try:
            cv2.line(self.images._inter_msk[self.id],
                     (d_x, d_y),
                     (new_d_x, new_d_y),
                     colour,
                     size)
        except cv2.error:
            # This error should no longer happen, but just incase message added
            self.print(f'Drawing error')
     
    @staticmethod
    def mouse_motion(event, images, widgets):
        pass

    @staticmethod
    def get_cursor():
        # override cursor
        return 'pencil'
    
    @staticmethod
    def generate_id(config):
        print('generate_id | Not used any more.')
        return
    
    def generate_name_text(self, path):
        text_name = f"{self.Type.__name__} | {path[self.config.rgb].split('/')[-1]}"
        return text_name
    
    def prepare_save(self):
        # Overidden from base class to allow the saving of the actual numpy array
        settings = {
            'type': type(self).__name__,
            'id': self.id,
            'text_name': self.text_name,
            'params': self.params,
            'drwmsk': self.images._inter_msk[self.id]
        }

        return settings
    
    def prepare_load(self, settings):
        # Overidden from base class to allow the saving of the actual numpy array
        self.id = settings['id']
        self.text_name = settings['text_name']
        self.params = settings['params']
        self.images._inter_msk[self.id] = settings['drwmsk']


class FinalSmooth(Base):
    # Upate Standard Plugin Type Configuration
    type_solo = True  # over write default 
    type_global = True  # Global plugin, affects all images
    type_create_on_tool_button = True  # Plugin instance is created when the tool is created

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
        # TODO push defaults to config file
        self.default_params = {
            'Active': True,         # True, False
            'Blur': 0.2,            # 0:1 as the blur is adjusted for the matrix for different zoom levels.
            'Threshold': 0.5,
            'RGB': True,            # Not used, but included for compatiblity
        }

        self.config = config
        self.id = id
        self.text_name = text_name
        self.is_global = is_global
        self.widgets = widgets
        self.widget_parent = widget_parent
        self.images = images
        # The values that are changes as the user interacts with the plugin
        self.params = copy.copy(self.default_params)    
        #self.filters = Filters()
        self.Type = FinalSmooth  # Can this be removed? Where is this value used?

        super().__init__(self.params)

    def make_button_tool(self, layout, tool_parent):
        # button_select_value
        name = 'button_final_smooth'
        image = 'blur'
        text = "Final Mask Smooth"
        value = "FinalSmooth"

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
        print('Start to make the widgets for the final blur: Blur')

        # Note: The Active checkbox is made by RockBase Class

        # label Blur
        self.widgets['label_final_blur_blur'] = ttk.Label(
            self.widget_parent,
            text='Smooth',
            state=ACTIVE,
            bootstyle=(DEFAULT,) 
        )

        self.widgets['label_final_blur_blur'].pack(
            self.config.standard_label
        )

        # Scale Blur 
        self.widgets['scale_final_blur_blur'] = ttk.Scale(
            self.widget_parent,
            command=None,
            value=self.params['Blur'],  
            state=ACTIVE,
            bootstyle=(DEFAULT,) 
        )

        self.widgets['scale_final_blur_blur'].pack(
            self.config.standard_scale
        )

        # label Offset
        self.widgets['label_final_blur_offset'] = ttk.Label(
            self.widget_parent,
            text='Offset',
            state=ACTIVE,
            bootstyle=(DEFAULT,) 
        )

        self.widgets['label_final_blur_offset'].pack(
            self.config.standard_label
        )

        # Scale Offset 
        self.widgets['scale_final_blur_offset'] = ttk.Scale(
            self.widget_parent,
            command=None,
            value=self.params['Threshold'],  
            state=ACTIVE,
            bootstyle=(DEFAULT,) 
        )

        self.widgets['scale_final_blur_offset'].pack(
            self.config.standard_scale
        )

        ToolTip(self.widgets['scale_final_blur_blur'], text="Change Blur Amount")

    def apply(self, changed_params=True, over_secondary=False):
        if changed_params:
            # Get the values from the scales (change to right type and range done in convert fuction)
            blur = self.widgets['scale_final_blur_blur'].get()
            threshold = self.widgets['scale_final_blur_offset'].get()

            self.params.update({
                'Blur': blur,
                'Threshold': threshold,
            })

    def delete_mask_or_interp(self):
        pass

    def mouse_select_value(self, event, over_secondary):
        pass
        #print(f'{self.Type}: Show something happened', event) 

    @staticmethod
    def mouse_motion(event, images, widgets):
        pass

    @staticmethod
    def get_cursor():
        # override cursor
        return ''
    
    @staticmethod
    def generate_id(config):
        return config.drwmsk
    
    def generate_name_text(self, path=None):
        text_name = f"Final Mask Smooth"
        return text_name
    

class SelectValue(Base):
    # Plugin Configuration
    type_global = True  
    type_mask = True
    type_create_on_first_click = True

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
        # TODO push defaults to config file
        self.default_params = {
            'Active': True,                 # True, False
            'Remove': True,                 # True Remove, False Keep
            'RGB': True,                    # True if apply to RGB, False apply to Dip
            'Hue': 60,                      # Update 180
            'Saturation': 127,              # Update 255
            'Value': 127,                   # Update 255
            'Hue threshold': 9,             # Update 180
            'Saturation threshold': 9,      # Update 255
            'Value threshold': 9,           # Update 255
            'Erode': 9,                   # 0 - 255
            'Dilate':9,                  # 0 - 255
            'Blur': 9,                    # 0 - 255
            'Threshold': 127,               # 0 - 255 # This is really a blur offset so keep at 0.5
            'Manual_mask': None,            # new mask is always created...
        }

        self.config = config
        self.id = id
        self.text_name = text_name
        self.is_global = is_global
        self.widgets = widgets
        self.widget_parent = widget_parent
        self.images = images

        # The values that are changes as the user interacts with the plugin
        self.params = copy.copy(self.default_params)    
        self.filters = Filters()

        self.Type = SelectValue  # Can this be removed? Where is this value used?
        # self.event_scale_change = event_scale_change
        # self.event_checkbox_change = event_checkbox_change

        super().__init__(self.params)

    def make_button_tool(self, layout, tool_parent):
        # button_select_value
        name = 'button_select_value'
        image = 'select_value'
        text = "Select Value"
        value = "SelectValue"
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
        print('SelectValue: Start to make the widgets for the properties')

        # Note: The Active checkbox is made by RockBase Class

        # Checkbutton keep
        self.widgets['checkbutton_select_value_keep'] = ttk.Checkbutton(
            self.widget_parent,
            text='Keep / Remove',
            bootstyle=(DEFAULT, TOGGLE, ROUND),
        )

        # TODO this should not be state but value? or something? fix
        # chk.state(['selected'])  # check the checkbox
        # chk.state(['!selected']) # clear the checkbox
        self.widgets['checkbutton_select_value_keep'].pack(
            side=TOP,
            ipadx=4,
            ipady=4,
            padx=1,
            pady=1,
        )

        if self.params['Remove']:
            self.widgets['checkbutton_select_value_keep'].state(['selected'])
        else:
            self.widgets['checkbutton_select_value_keep'].state(['!selected'])

        ToolTip(self.widgets['checkbutton_select_value_keep'], text="Keep if off. Remove if on.")       

        # Horizontal Separator
        name = 'separator_select_value_start'
        self.widgets[name] = ttk.Separator(
            self.widget_parent,
            orient=HORIZONTAL,
            bootstyle=(DEFAULT),
        )
        self.widgets[name].pack(
            side=TOP, 
            fill=X,
            #ipadx=4,
            ipady=4,
            #padx=1,
            pady=1,
        )

        # label color picker
        self.widgets['label_color_picker'] = ttk.Label(
            self.widget_parent,
            text='Colour Picker',
            state=ACTIVE,
            bootstyle=(DEFAULT,) 
        )

        self.widgets['label_color_picker'].pack(
            self.config.standard_label
        )

        # New custom colour picker
        self.widgets['colorpicker_select_value'] = ColorPicker(
            self.widget_parent,
            show_selected=True
        )
        self.widgets['colorpicker_select_value'].set_hsv_colour(
            color = (
                self.params['Hue'],
                self.params['Saturation'],
                self.params['Value']
            )
        )
        self.widgets['colorpicker_select_value'].pack(
            side=TOP,
            ipadx=4,
            ipady=4,
            padx=1,
            pady=1,
        )

        # Horizontal Separator
        name = 'separator_select_value_middle'
        self.widgets[name] = ttk.Separator(
            self.widget_parent,
            orient=HORIZONTAL,
            bootstyle=(DEFAULT),
        )
        self.widgets[name].pack(
            side=TOP, 
            fill=X,
            #ipadx=4,
            ipady=4,
            #padx=1,
            pady=1,
        )

        # label Threshold
        self.widgets['label_select_value_threshold'] = ttk.Label(
            self.widget_parent,
            text='Threshold',
            state=ACTIVE,
            bootstyle=(DEFAULT,) 
        )

        self.widgets['label_select_value_threshold'].pack(
            self.config.standard_label
        )

        # Scale Threshold
        self.widgets['scale_select_value_threshold'] = ttk.Scale(
            self.widget_parent,
            value=self.params['Hue threshold'],  
            state=ACTIVE,
            bootstyle=(DEFAULT),
            from_=0,
            to=64, 
        )

        self.widgets['scale_select_value_threshold'].pack(
            self.config.standard_scale
        )

        ToolTip(self.widgets['scale_select_value_threshold'], text="Change Threshold")

        # label smooth
        self.widgets['label_select_value_smooth'] = ttk.Label(
            self.widget_parent,
            text='Smooth',
            state=ACTIVE,
            bootstyle=(DEFAULT,) 
        )

        self.widgets['label_select_value_smooth'].pack(
            self.config.standard_label
        )

        # Scale smooth
        self.widgets['scale_select_value_smooth'] = ttk.Scale(
            self.widget_parent,
            #command=partial(self.event_scale_change, self.id),
            value=self.params['Blur'],  
            state=ACTIVE,
            bootstyle=(DEFAULT,),
            from_=0,
            to=64, 
        )

        self.widgets['scale_select_value_smooth'].pack(
            self.config.standard_scale
        )

        ToolTip(self.widgets['scale_select_value_smooth'], text="Change Smoothing")

    def apply(self, changed_params=True, over_secondary=False):
        print(f'{time.time()}: Start the processing of the images here...')

        if changed_params:
            # Get the values from the scales (change to right type and range done in convert fuction)
            remove = self.widgets['checkbutton_select_value_keep'].instate(['selected'])
            hue, saturation, value = self.widgets['colorpicker_select_value'].get_hsv_colour()
            print(f'apply | changed_params | colorpicker: {hue, saturation, value}')

            smooth = self.widgets['scale_select_value_smooth'].get()
            hsv_threshold = self.widgets['scale_select_value_threshold'].get()

            self.params.update({
                'Remove': remove,
                'Hue': hue,
                'Saturation': saturation,
                'Value': value,
                'Hue threshold': hsv_threshold,
                'Saturation threshold': hsv_threshold,
                'Value threshold': hsv_threshold,
                'Erode': 0,
                'Dilate': smooth,
                'Blur': smooth,
                'Threshold': 127, # This is really a blur offset so keep at 0.5 
            })
        else:
            # Note: RGB vs Dip can only be set on the initial mouse select
            #       IE not possible to update this after creation of plugin instance.
            self.params['RGB'] = not over_secondary

        # else the params are already setup from the user selection
        converted = self.convert_params()

        print('Converted Params', converted)

        if not over_secondary:
            mask = self.apply_simple_hue(
                converted,
                self.images._in[self.config.hsv],
                self.params['Remove'],
            )
        else:
            mask = self.apply_simple_hue(
                converted,
                self.images._in[self.config.diphsv],
                self.params['Remove'],
            )

        # Add new mask to the system
        self.images._inter_msk[self.id] = mask 
        print(f'{time.time()}: Finished the processing of the images. Mask: {mask.shape}')

    def apply_simple_hue(self, filter_parameter, img, remove=False):
        # Groupings of settings
        rgb_colours_to_mask = []
        rgb_colour_thresholds = []
        rgb_colour_edbats = []

        # From more complex old way - starting to be simpler
        rgb_colours_to_mask.append([
            filter_parameter['Hue'],
            filter_parameter['Saturation'],
            filter_parameter['Value']
        ])
        rgb_colour_thresholds.append([
            filter_parameter['Hue threshold'],
            filter_parameter['Saturation threshold'],
            filter_parameter['Value threshold']
        ])
        rgb_colour_edbats.append([
            filter_parameter['Erode'],
            filter_parameter['Dilate'],
            filter_parameter['Blur'],
            filter_parameter['Threshold']
        ])
        
        if remove:
            mask_hsv = self.filters.simple_by_hsv_colors(
                img=img,
                type=None,
                colours=rgb_colours_to_mask,
                thresholds=rgb_colour_thresholds,
                edbats=rgb_colour_edbats,
                invert_output=True
            )  # True to Remove
        else:
            mask_hsv = self.filters.simple_by_hsv_colors(
                img=img,
                type=None,
                colours=rgb_colours_to_mask,
                thresholds=rgb_colour_thresholds,
                edbats=rgb_colour_edbats,
                invert_output=False
            )  # False to keep
    
        return mask_hsv
    
    def generate_name_text(self, path=None):
        params = self.convert_params()
        colour = (
            params['Hue'],
            params['Saturation'],
            params['Value']
        )
        print("generate_name_text", colour)
        colour = rb_colour_to_name.get_colour_name(colour ,hsv=True)

        if self.params['RGB']:
            RGB_dip = 'RGB'
        else:
            RGB_dip = 'Dip'

        if self.params['Remove']:
            keep_remove = 'Remove'
        else:
            keep_remove = 'Keep'

        name = f"{RGB_dip} | {keep_remove} | {colour}" 

        return name
    
    def convert_params(self):
        '''Change from widget values to filter values'''
        params = copy.copy(self.params) 
        
        erode = 0
        if params['Blur'] > 50: # 13 original value
            erode = 1
        
        smooth = self.params['Blur']

        params['Active'] = self.params['Active'],
        params['Type'] = 'Undefined For Now'
        params['Hue'] = int(self.params['Hue'])
        params['Saturation'] = int(self.params['Saturation'])
        params['Value'] = int(self.params['Value'])
        params['Hue threshold'] = int(self.params['Hue threshold'])
        params['Saturation threshold'] = int(self.params['Saturation threshold'])
        params['Value threshold'] = int(self.params['Value threshold'])
        params['Erode'] = int(erode)
        params['Dilate'] = int(smooth)
        params['Blur'] = int(smooth * 2)
        params['Threshold'] = int(self.params['Threshold'])
 
        return params
    
    def delete_mask_or_interp(self):
        del self.images._inter_msk[self.id]
    
    def mouse_select_value(self, event, over_secondary): 
        # Guard clause for wrong event type
        if event == None:
            return
        if not (event.type == EventType.ButtonRelease and event.num == 1):
            return

        if not over_secondary:
            hsv = self.images.screen_coords_to_hsv(event.x, event.y)
        else:
            hsv = self.images.screen_coords_to_hsv(event.x, event.y, over_secondary)  
        
        self.params['Hue'] = hsv[0]
        self.params['Saturation'] = hsv[1]
        self.params['Value'] = hsv[2]
        self.params['RGB'] = not over_secondary

        self.widgets['colorpicker_select_value'].set_hsv_colour(
            color = (
                self.params['Hue'],
                self.params['Saturation'],
                self.params['Value'],
            )
        )

        print('mouse selected value', hsv) 
        print('convert_params: ', self.convert_params())

    @staticmethod
    def mouse_motion(event, images, widgets):
        colour = images.screen_coords_to_hex(event.x, event.y)
        offset_x = -10
        offset_y = 10
        
        over_primary = False
        over_secondary = False
        if event.widget == widgets['label_view_upper']:
            over_primary = True
        if event.widget == widgets['label_view_lower']:
            over_secondary = True

        if colour == '-1' or (not over_secondary and not over_primary) : # if images says there is no colours from the img
            if widgets.get('mouse_rect_upper', False):
                widgets['mouse_rect_upper'].place_forget()
            if widgets.get('mouse_rect_lower', False):
                widgets['mouse_rect_lower'].place_forget()
            if widgets.get('mouse_point_upper', False):
                widgets['mouse_point_upper'].place_forget()
            if widgets.get('mouse_point_lower', False):
                widgets['mouse_point_lower'].place_forget()
        else:
            # if the mouse_rect_upper exist
            if widgets.get('mouse_rect_upper'): 
                # update colour and move the rectangle
                widgets['mouse_rect_upper'].config(
                    background=images.screen_coords_to_hex(event.x, event.y),
                )
                widgets['mouse_rect_upper'].place(x=event.x-offset_x, y=event.y + offset_y)

                widgets['mouse_rect_lower'].config(
                    background=images.screen_coords_to_hex(event.x, event.y, secondary=True),
                )
                widgets['mouse_rect_lower'].place(x=event.x-offset_x, y=event.y + offset_y)
            else:
                # mouse_circles don't exist so create them and set color
                widgets['mouse_rect_upper'] = ttk.Label(
                    widgets['label_view_upper'], 
                    background=images.screen_coords_to_hex(event.x, event.y),
                    text='     ',
                    borderwidth=1,
                    relief='solid'
                )
                widgets['mouse_rect_upper'].place(x=event.x-offset_x, y=event.y + offset_y)

                widgets['mouse_rect_lower'] = ttk.Label(
                    widgets['label_view_lower'], 
                    background=images.screen_coords_to_hex(event.x, event.y, secondary=True),
                    text='     ',
                    borderwidth=1,
                    relief='solid'
                )
                widgets['mouse_rect_lower'].place(x=event.x-offset_x, y=event.y + offset_y)

            if widgets.get('mouse_point_upper') and widgets.get('mouse_point_lower'):
                # move mouse point were users mouse is exactly
                if over_secondary:
                    widgets['mouse_point_upper'].place(x=event.x-1, y=event.y-1)
                    widgets['mouse_point_lower'].place_forget()
                else:
                    widgets['mouse_point_lower'].place(x=event.x-1, y=event.y-1)
                    widgets['mouse_point_upper'].place_forget()
            else:
               # mouse point don't exist so create them and set were mouse is exactly
                if over_secondary:
                    if not widgets.get('mouse_point_upper', False):
                        widgets['mouse_point_upper'] = ttk.Label(
                            widgets['label_view_upper'], 
                        )
                        circle = cv2.imread('./resources/target.png', 0)
                        circle = cv2.resize(circle, (2,2))
                        widgets['img_circle_upper'] = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(circle))
                        widgets['mouse_point_upper'].configure(image=widgets['img_circle_upper'])
                    widgets['mouse_point_upper'].place(x=event.x-1, y=event.y-1)
                else:
                    if not widgets.get('mouse_point_lower', False):
                        widgets['mouse_point_lower'] = ttk.Label(
                            widgets['label_view_lower'], 
                        )
                        circle = cv2.imread('./resources/target.png', 0)
                        circle = cv2.resize(circle, (2,2))
                        widgets['img_circle_lower'] = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(circle))
                        widgets['mouse_point_lower'].configure(image=widgets['img_circle_lower'])
                    widgets['mouse_point_lower'].place(x=event.x-1, y=event.y-1)

    @staticmethod
    def get_cursor():
        # override cursor
        return 'tcross'
    
    def prepare_save(self):
        settings = {
            'type': type(self).__name__,
            'id': self.id,
            'text_name': self.text_name,
            'is_global': self.is_global,
            'params': self.params
        }

        return settings

from abc import ABC, abstractclassmethod
from ttkbootstrap.constants import *

from rb_types import *


class Base(ABC):
     # Standard Plugin Type Configuration
    type_solo = False  # True if only one of this class can exist
    type_needs_apply = True  # True if plugin need to be applied by button press. 
                             # For plugin which take longer than ~0.2ms to run on large images.
    type_has_popup = False   # Has a left click menu with options 

    type_view = False  # Only changes the view 

    # Pair below are exclusive
    type_draw = False  # Allows mouse drawing (manual corrections)
    type_mouse_events = False  # Allows mouse events - seperate from drawn layers

    # Pair below are exclusive
    type_mask = False  # Generates a mask layer
    type_interp = False # Generate a interp layer
    
    # Pair below are exclusive
    type_global = False  # Global plugin, affects all images
    type_local = False  # local plugin, only affect specific images
    
    # Pair below are exclusive
    type_create_on_first_click = False  # Plugin instance is created when the user clicks image/selects value
    type_create_on_tool_button = False  # Plugin instance is created when the tool is created
    
    @abstractclassmethod
    def __init__(self, 
                 params=None,
                 ):
        self.params = params

    @abstractclassmethod
    def make_button_tool(self):
        pass

    @abstractclassmethod
    def make_widgets(self):
        pass

    @abstractclassmethod
    def apply(self, mask):
        pass

    @abstractclassmethod
    def delete_mask_or_interp(self):
        pass

    def prepare_save(self):
        settings = {
            'type': type(self).__name__,
            'id': self.id,
            'text_name': self.text_name,
            #'is_global': self.is_global, # The plugin type holds this information
            'params': self.params
        }

        return settings

    def prepare_load(self, settings):
        self.id = settings['id']
        self.text_name = settings['text_name']
        #self.is_global = settings['is_global'] # The plugin type holds this information
        self.params = settings['params']

    def self_mouse_motion(self, event):
        pass

    @abstractclassmethod
    def get_cursor(self):
        pass

    @abstractclassmethod
    def generate_name_text(self, path=None):
        pass
    

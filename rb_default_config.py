import dataclasses
import dataclasses_json
from rb_types import View
from ttkbootstrap.constants import *

@dataclasses_json.dataclass_json
@dataclasses.dataclass
class Config:
    resources_path: str = "./resources/"

    recent_path_0: str = ""
    recent_path_1: str = ""
    recent_path_2: str = ""

    image_filetypes: tuple = (
        ('tif', '*.tif'),
        ('tiff', '*.tiff'),
        ('png', '*.png'),
        ('jpg', '*.jpg'),
        ('jpeg', '*.jpeg'),
        ('bmp', '*.bmp')
    )

    accepted_formats: tuple = (
        'tif', 
        'tiff', 
        'png', 
        'jpg', 
        'jpeg', 
        'bmp'
    )

    # Fixed Layers
    rgb: str = 'rgb'        # red, green, blue
    dip: str = 'dip'        # dip or verticality
    msk: str = 'msk'        # mask
    drwmsk: str = 'drwmsk'  # manually draw annotation to mask
    KOL: str = 'KOL'        # 'K'eep 'O'ut'L'ine
    hsv: str = 'hsv'        # hue saturation value
    diphsv: str = 'diphsv'  # hue saturation value for dip image
    obs: str = 'obs'        # Observation
    drwobs: str = 'drwobs'  # manually draw annotation to Observation
    int: str = 'int'        # interpretation
    drwint: str = 'drwint'  # manually draw annotation to interpretation
    
    # constants
    max_width: int = 32000
    max_height: int = 6666
    max_pixels: int = max_width * max_height
    force_grayscale_dip: bool = False
    keep_outline_size: int = 3                  # For keep_regions outline size
    interpolation_type: int = 0
    warn_about_resize: bool = True              # Not used
    exaggerate_vertically_by: float = 1         # Not used in this version

    # Keyboard Effects
    pan_step: int = 50                          # How much the keyboard input pans image
    minimum_draw = 5
    maximum_draw = 500

    # For loading 
    starting_rgb_path: str = "./outcrop/ExportPanel00001_RGB.tif"
    starting_dip_path: str = "./outcrop/ExportPanel00001_Dip.tif"
    blank_image_path: str = "§blank_image_path§"  # Can't be first image, first is need to define dimensions

    # Plugin Modules to load {module_name: internal_name}
    plugin_modules: tuple = (
        ('rb_plugin_standard','plugin_standard'),
        ('rb_plugin_rock_clean','plugin_rock_clean'),
        ('rb_plugin_rock_lens', 'plugin_rock_lens'),
        ('rb_plugin_split_assign', 'plugin_split_assign'),
    )

    # Default or Starting colours for masks and interps
    blank_image_colour: tuple = (0, 0, 0)
    blank_mask_colour: int = 127
    blank_interp_colour: tuple = (0, 0, 0)
    blank_mouse_over: tuple = (0, 0, 0)

    # Colours for outlines and mouse_overs
    keep_outline_zero_channel = 2  # Zero this channel to make simple colour from mask
    mouse_over_colour = (255, 255, 0)
    
    # Persistant view settings
    view: View = View.DOUBLE
    show_explorer: bool = False
        
    # Drawing - TODO Check is this still used?
    draw_size: int = 64
    draw_size_max: int = 640
    draw_size_shrink: float = 0.8
    draw_size_grow: float = 1.2

    # Default Rock Types for Interp.
    # BGR, 0-255 colours
    rock_types = {
        'Outside Outcrop | Cyan': (255, 255, 0), # cyan
        'Sandstone | Yellow': (0, 255, 255), # yellow
        'Other 1 | Magenta': (255, 0 , 255), # Magenta
        'Other 2 | Red': (0, 0, 255),  # Red
        'Vegetation | Green': (0, 255, 0),  # Green 
        'Other 3 | Blue': (255, 0, 0),  # Blue 
        'Mudstone | Light Grey': (196, 196, 196),  # light gray 
        'Mudstone | Medium Grey': (128, 128, 128),  # gray 
        'Coal | Dark Grey': (64, 64, 64),  # very dark gray almost black 
        'Null | Black': (0,0,0), # Black
    }
    default_rock_type = 'Outside Outcrop | Cyan'

    # Map from colours to class for RockLens
    class_to_colour = {
        1: (255, 255, 0), # cyan
        2: (0, 255, 255), # yellow
        3: (255, 0 , 255), # Magenta
        4: (0, 0, 255),  # Red
        5: (0, 255, 0),  # Green 
        6: (255, 0, 0),  # Blue 
        7: (196, 196, 196),  # light  gray 
        8: (128, 128, 128),  # gray 
        9: (64, 64, 64),  # very dark gray almost black 
        0: (0,0,0), # Black
    }

    # Look and feel
    # Note difficult to get balance between large display on macOS and 
    # Windows Normal display
    dark_theme: bool = True
    button_tool_width:int = 40      # Used for standard tool buttons
    button_tool_height:int = 40
    button_layout_width: int = 40   # Used for Double vs Single View
    button_layout_height: int = 40

    # Widget Styles - Keyword Arguements
    standard_scale = {
        'side':TOP,
        'fill':X,
        'expand':True,
        'ipadx':4,
        'ipady':2,
        'padx':14,
        'pady':2,
    }

    standard_label = {
        'side':TOP,
        'ipadx':4,
        'ipady':4,
        'padx':4,
        'pady':4,
    }

    standard_button_tool = {
        'side':TOP,
        'ipadx':0,
        'ipady':0,
        'padx':2,
        'pady':2,
    }

    standard_button_view = {
        'side':RIGHT,
        'ipadx':0,
        'ipady':0,
        'padx':2,
        'pady':2,
    }



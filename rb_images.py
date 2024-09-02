import copy
import cv2
import math
import numpy as np
import os
from rb_filters import Filters  # Need this for combining masks


class Images():
    def __init__(self, config, plugins) -> None:
        # INFUTURE: Rename dictionaries to in | msk | obs | int | out
        self._in = {}               # raw input files, full resolution
        self._inter_msk = {}        # intermediate images of the mask
        self._inter_int = {}        # intermediate images of the interp - this stage should be rename observations thus obs
        self._inter_ui = {}         # intermediate images which are for the ui, mainly mouse_over temp. highlights
        self._out = {}              # low resolution and crops of current ROI / zoomed out / preview

        self.config = config
        self.plugins = plugins

        self.image_width = None
        self.image_height = None
        self.image_channels = None

        self.view_width = None
        self.view_height = None

        self.draw_circle_size = None

        # TODO - Still needed? The plugins being active is used instead? 20240125
        #self.active_layers = []

        self.needs_update = False

        self.matrix = np.array([[1, 0, 0], [0, 1, 0]], dtype=np.float32)  # Matrix for translate / zoom
        self.interpolations = [cv2.INTER_NEAREST, cv2.INTER_LINEAR, cv2.INTER_CUBIC, cv2.INTER_AREA]

        self.filters = Filters()

    # Create, Read: Also check...
    def paths_exist(self, paths, accepted_formats):
        """Check the files at the paths exist and have the correct extension"""
        status = None
        message = None
        for path in paths.values():
            if os.path.isfile(path) and path.rsplit('.', 1)[-1] in accepted_formats:
                status = True
                message = ''
            elif path == self.config.blank_image_path:
                status = True
                message = ''
            else:
                status = False
                message = f'Either path does not lead to file, or wrong file format: {path}'
                break

        return status, message

    def load_single(self, path):
        # Check the 1 path are passed
        assert len(path) == 1, "Error expected one path"
        files_exist, message = self._load(path)
        return files_exist, message
    
    def load_rgb_dip(self, paths):
        # Check the 2 paths are passed
        assert len(paths) == 2, "Error expected two paths"
        files_exist, message = self._load(paths)
        return files_exist, message
    
    def _load(self, paths):
        # Check the paths exist
        files_ok, message = self.paths_exist(paths, self.config.accepted_formats)

        if not files_ok:
            return files_ok, message
 
        if paths.get(self.config.rgb, False):
            # if path contains rgb overwrite existing
            self.paths = paths  # For future reference
        else:
            # else add to the paths
            self.paths.update(paths)
            

        for layer_type, path in paths.items():
            if not path == self.config.blank_image_path:
                try:
                    if layer_type == self.config.rgb:
                        self._in[layer_type] = cv2.imread(path, cv2.IMREAD_COLOR) #cv2.IMREAD_UNCHANGED)
                        # If rgb file, set height and width as definitive for image set
                        self.image_height, self.image_width, self.image_channels = self._in[self.config.rgb].shape
                    elif layer_type == self.config.drwmsk: # The masks have to be grayscale...
                        self._in[layer_type] = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
                        self._in[layer_type] = cv2.bitwise_not(self._in[layer_type])
                        # Check all other images against existing rgb layer
                        height_ok = self._in[layer_type].shape[0] == self.image_height
                        width_ok = self._in[layer_type].shape[1] == self.image_width
                        if (not height_ok) or (not width_ok):
                            files_ok = False
                            message = f"{layer_type} file does not match size of RGB file."
                            return files_ok, message    
                    else:
                        self._in[layer_type] = cv2.imread(path, cv2.IMREAD_COLOR) #cv2.IMREAD_UNCHANGED)
                        # Check all other images against existing rgb layer
                        height_ok = self._in[layer_type].shape[0] == self.image_height
                        width_ok = self._in[layer_type].shape[1] == self.image_width
                        if (not height_ok) or (not width_ok):
                            files_ok = False
                            message = f"{layer_type} file does not match size of RGB file."
                            return files_ok, message
                        
                    print(f"Loaded path: {path}, to layer: {layer_type}")
                except RuntimeWarning:
                    print(f"Warning could not load path: {path}")
                    # TODO Propagate this back to the GUI
            else:
                img = np.ones((self.image_height, self.image_width, self.image_channels), dtype=np.uint8)
                img *= np.array(self.config.blank_image_colour, dtype=np.uint8)
                self._in[layer_type] = img

        # Store HSV versions of the rgb and dip images
        self._in[self.config.hsv] = (cv2.cvtColor(self._in[self.config.rgb], cv2.COLOR_BGR2HSV))
        self._in[self.config.diphsv] = (cv2.cvtColor(self._in[self.config.dip], cv2.COLOR_BGR2HSV))

        # Initial matrix and Centre Image and zoom out
        self.matrix = np.array([[1, 0, 0], [0, 1, 0]], dtype=np.float32)  # Matrix for translate / zoom

        delta = (1389 / self.image_width) * 0.9
        self.matrix = self.matrix * delta
        if self.view_height != None:
            self.matrix[0, 2] += (self.view_width / 2) * (0.1)
            self.matrix[1, 2] += (self.view_height / 2) * (0.1)
        else:
            self.matrix[0, 2] += (1389 / 2) * (0.1)
            self.matrix[1, 2] += (429 / 2) * (0.1)          
    
        print('load: self.matrix', self.matrix)

        return files_ok, message

    # Update: export to disk 
    def export_mask(self, path, threshold, blur):
        cv2.imwrite(path, self.combine_masks_for_export(final_threshold=threshold, final_blur=blur))

    # Other Functions
    def zoom(self, delta):
        # The zooms to top left corner
        self.matrix = self.matrix * delta

        # keep image on center
        if delta > 1:
            self.matrix[0, 2] -= (self.view_width / 2) * 0.1
            self.matrix[1, 2] -= (self.view_height / 2) * 0.1
        else:
            self.matrix[0, 2] += (self.view_width / 2) * 0.1
            self.matrix[1, 2] += (self.view_height / 2) * 0.1

        print('Zoom: self.matrix', self.matrix, delta, 'w:h', self.view_width,':', self.view_height)

    def pan(self, screen_xy, delta):
        delta *= -1
        # "zoom" coord space
        if screen_xy == 'screen_x':
            self.matrix[0, 2] += delta
        if screen_xy == 'screen_y':
            self.matrix[1, 2] += delta

        print('pan: self.matrix', self.matrix)

    def resize_draw_cirle(self, delta):
        if self.draw_circle_size:
            self.draw_circle_size = int(self.draw_circle_size * delta)

            if self.draw_circle_size < self.config.minimum_draw:
                self.draw_circle_size = self.config.minimum_draw
            elif self.draw_circle_size > self.config.maximum_draw:
                self.draw_circle_size = self.config.maximum_draw

    def keep_proportions(self, x, y):
        pixel_count = x * y

        # Exaggerate Vertically - Do this before calculating area...
        y *= self.config.exaggerate_vertically_by

        scale = 1
        if pixel_count > self.MAX_PIXELS:

            if self.WARN_ABOUT_RESIZE:
                # ToDo fix this 
                # [ ] need to be handled in the main app not here...
                print('Images Are Too Large For Interactive Use')
                # tk_messagebox.showwarning(f'Images Are Too Large For Interactive Use',
                #                           f'As the images are larger than {self.MAX_PIXELS // 1000000} Megapixels'
                #                           f' they will be proportionally resized.')

            scale = math.sqrt((x * y) / self.MAX_PIXELS)

        _x = int(x / scale)
        _y = int(y / scale)

        return _x, _y

    def transform_view_to_array(self, x, y):
        x_ = round((x / self.matrix[0, 0]) - (self.matrix[0, 2] / self.matrix[0, 0]))
        y_ = round((y / self.matrix[1, 1]) - (self.matrix[1, 2] / self.matrix[1, 1]))
        return x_, y_

    def transform_view2buffer(self, x, y):
        x_ = round((x / self.matrix[0, 0]) - (self.matrix[0, 2] / self.matrix[0, 0]))
        y_ = round((y / self.matrix[1, 1]) - (self.matrix[1, 2] / self.matrix[1, 1]))
        return x_, y_
    
    def screen_coords_to_hsv(self, x_, y_, secondary=False):     
        # Convert coordinates
        x, y = self.transform_view_to_array(x_, y_)

        # Guard against being out of range or image not loaded
        if self._in.get(self.config.rgb) is None:
            hsv = '-1'
        elif not self.inbounds(x_, y_):
            hsv = '-1'
        else:
            if secondary:
                hsv = self._in[self.config.diphsv][y, x]
            else: # use the rgb image
                hsv = self._in[self.config.hsv][y, x]
        
        return hsv        
    
    def screen_coords_to_hex(self, x_, y_, secondary=False, order_rgb=True):
        # TODO:
        # make this check if mode=empty
        # then remove the if not self.img_rgb is None - the mode controls this not the img array values
        
        # Convert coordinates
        x, y = self.transform_view_to_array(x_, y_)

        # Guard against being out of range
        if self._in.get(self.config.rgb) is None:
            fill_hex = '-1'
        elif not self.inbounds(x_, y_):
            fill_hex = '-1'
        else:
            if secondary:
                colours = self._in[self.config.dip][y, x]
            else: # use the rbn image
                colours = self._in[self.config.rgb][y, x]
            
            if order_rgb:
                fill_hex = f'#{hex(colours[2])[2:].zfill(2)}{hex(colours[1])[2:].zfill(2)}{hex(colours[0])[2:].zfill(2)}'
            else:
                fill_hex = f'#{hex(colours[0])[2:].zfill(2)}{hex(colours[1])[2:].zfill(2)}{hex(colours[2])[2:].zfill(2)}'
        return fill_hex

    def inbounds(self, x_, y_):
        # return true if image exists and coordinates are within the bounds of the image (inside a 1 boarder)

        x, y = self.transform_view_to_array(x_, y_)

        if self._in.get(self.config.rgb) is not None:
            max_height, max_width, c = self._in[self.config.rgb].shape
            if x > 1 and (x < max_width - 1) and y > 1 and (y < max_height - 1):
                inbounds = True
            else:
                inbounds = False
            return inbounds
        else:
            inbounds = False

        return inbounds

    def limit_inbounds(self, x, y):
        # keep the x and y coordinates in bounds of rgb (archtype) image
        if x < 0:
            x = 0
        if y < 0: 
            y = 0
        
        if x >= self._in[self.config.rgb].shape[1] - 1:
            x = self._in[self.config.rgb].shape[1] -1
        if y >= self._in[self.config.rgb].shape[0] -1 :
            y = self._in[self.config.rgb].shape[0] -1

        return x, y
        
    def combine_masks_for_export(self, final_threshold, final_blur=1):
        # All the stacking of masks will happen in the methods below here
               
        # Guard Clause: Check there are images loaded by looking at image_height
        if self.image_height is None:
            return
        
        # We need to create multiple blank, 255, output masks before we can start
        w = self.image_width
        h = self.image_height
        msk_remove = np.zeros((h, w), dtype=np.uint8)
        msk_keep = np.zeros((h, w), dtype=np.uint8)
        msk_remove[:, :] = 255
        msk_keep[:, :] = 0
        draw_mask_id = None
        
        # Loop through all the plugins  
        for plugin in self.plugins:
            active = self.plugins[plugin].params.get("Active", False)
            type_mask = self.plugins[plugin].type_mask
            type_draw = self.plugins[plugin].type_draw
            type_view = self.plugins[plugin].type_view

            # We need to know if there are any drawn masks
            if type(self.plugins[plugin]).__name__ == 'DrawMask' and \
                self.plugins[plugin].params['Active']:
                draw_mask_id = plugin

            if active and type_mask and (not type_draw) and (not type_view):
                remove = self.plugins[plugin].params.get("Remove", 'Error')
                if remove: # All the Remove filters anded together
                    msk_remove = self.filters.combine_masks_and(
                        msk_remove, 
                        self._inter_msk[plugin], 
                        [0, 0, final_blur, final_threshold]
                    )
                elif remove == 'Error':
                    return None
                else:  # All the keep filters or'd together
                    msk_keep = self.filters.combine_masks_or(
                        msk_keep, 
                        self._inter_msk[plugin], 
                        [0, 0, final_blur, final_threshold],
                        False
                    )       

        # If there is a draw mask merge into masks 
        # Must be done after apply other plugins to give higher precedence.
        if draw_mask_id:
            if draw_mask_id in self._inter_msk:
                mask = copy.copy(self._inter_msk[draw_mask_id])
                msk_remove = np.where(mask == 255, 0, msk_remove)
                msk_keep = np.where(mask == 0, 255, msk_keep)

        # Merge the keep and remove masks
        full_size_output = msk_remove | msk_keep      

        # Finally convert to 3 channel, need this for compatability else where in code
        full_size_output = cv2.cvtColor(full_size_output, cv2.COLOR_GRAY2RGB)

        return full_size_output

    def combine_masks(self, w, h, final_threshold, final_blur=1, keep_outline=True):  
        # All the stacking of masks will happen in the methods below here
               
        # Guard Clause: Check there are images loaded by looking at image_height
        if self.image_height is None:
            return
        
        # We need to create multiple blank, 255, output masks before we can start
        msk_remove = np.zeros((h, w), dtype=np.uint8)
        msk_keep = np.zeros((h, w), dtype=np.uint8)
        msk_remove[:, :] = 255
        msk_keep[:, :] = 0
        draw_mask_id = None
        
        # Loop through all the plugins  
        for plugin in self.plugins:
            active = self.plugins[plugin].params.get("Active", False)
            type_mask = self.plugins[plugin].type_mask
            type_draw = self.plugins[plugin].type_draw
            type_view = self.plugins[plugin].type_view

            # We need to know if there are any drawn masks
            if type(self.plugins[plugin]).__name__ == 'DrawMask' and \
                self.plugins[plugin].params['Active']:
                draw_mask_id = plugin

            if active and type_mask and (not type_draw) and (not type_view):
                remove = self.plugins[plugin].params.get("Remove", 'Error')
                if remove: # All the Remove filters anded together
                    # Apply transform so there is less to process
                    mask = cv2.warpAffine(
                        self._inter_msk[plugin], 
                        self.matrix, 
                        (w, h),
                        flags=self.interpolations[self.config.interpolation_type]
                    )
                    
                    msk_remove = self.filters.combine_masks_and(
                        msk_remove, 
                        mask, 
                        [0, 0, final_blur, final_threshold]
                    )
                else:  # All the keep filters or'd together
                    # Apply transform so there is less to process
                    mask = cv2.warpAffine(
                        self._inter_msk[plugin], 
                        self.matrix, 
                        (w, h),
                        flags=self.interpolations[self.config.interpolation_type]
                    )

                    msk_keep = self.filters.combine_masks_or(
                        msk_keep, 
                        mask, 
                        [0, 0, final_blur, final_threshold], # TODO apply to export also
                        False
                    )    

        # If there is a draw mask merge into masks 
        # Must be done after applying other plugins to give higher precedence.
        if draw_mask_id:
            if draw_mask_id in self._inter_msk:
                # warp it
                mask = cv2.warpAffine(
                    self._inter_msk[draw_mask_id], 
                    self.matrix, 
                    (w, h),
                    flags=self.interpolations[self.config.interpolation_type]
                )
                
                # TODO fix this:
                # Problem here which is overwriting the alternative state I believe
                msk_remove = np.where(mask == 255, 0, msk_remove)
                msk_keep = np.where(mask == 0, 255, msk_keep) # original 
                #msk_keep = np.where(mask != 255, 0, msk_keep) # <--- better?

        # Calculate the keep boarder
        if keep_outline:
            self._out[self.config.KOL] = self.show_keep_regions(msk_keep) 
        else:
            self._out[self.config.KOL] = None           

        # Merge the keep and remove masks
        self._out[self.config.msk] = msk_remove | msk_keep      
        
        # Finally convert to 3 channel for masking RGB image for output
        self._out[self.config.msk] = cv2.cvtColor(self._out[self.config.msk], cv2.COLOR_GRAY2RGB)

    def delete_layers_not_drawn(self):
        for plugin in self.plugins:
            if not self.plugins[plugin].type_draw:
                # Check for masks from this plugin
                result = self._inter_msk.get(plugin, False)
                if hasattr(result, "shape"):
                    del(self._inter_msk[plugin])

                # Check for interps from this plugin
                result = self._inter_int.get(plugin, False)
                if hasattr(result, "shape"):
                    del(self._inter_int[plugin])
    
    def show_keep_regions(self, mask_keep):
        # Create the keep outline image
        kernel = np.ones((self.config.keep_outline_size, self.config.keep_outline_size), np.uint8)
        img_keep_outline = cv2.dilate(mask_keep, kernel)
        img_keep_outline = cv2.bitwise_and(img_keep_outline, cv2.bitwise_not(mask_keep))
        img_keep_outline = cv2.cvtColor(img_keep_outline, cv2.COLOR_GRAY2BGR)
        self.config.keep_outline_zero_channel
        img_keep_outline[:, :, self.config.keep_outline_zero_channel] = 0  # Zero channel to make simple colour from mask.
        return img_keep_outline

    def update_single(self, 
                      w, 
                      h, 
                      keep_background=0.5,
                      show_interp=0.5, 
                      keep_outline=True,
                      mouse_x=None,
                      mouse_y=None,
                      ): 
        # Apply warpaffine - Order of operations
        #   1   Resize pan zoom RGB image
        #   2   if there are masks
        #       resize/pan/zoom them, combine them and global blur them
        #       force manual mask corrections on top
        #       alpha blend remove region with keep region
        #       alpha blend INTERP with result of above
        #       return final image
        #       TODO 
        #       force interp. on top as alpha blended layer
        print(f"{self}|  update_single | Plugins: {self.plugins}")
 
        self.view_width, self.view_height = float(w), float(h)
        
        img_out_rgb = cv2.warpAffine(self._in[self.config.rgb], 
                                    self.matrix, 
                                    (w, h),
                                    flags=self.interpolations[self.config.interpolation_type])

        # We need to know the FinalSmooth 'Blur' value before we can update
        # Loop through all the plugins 
        final_blur=1 
        final_threshold = 0.5 
        for plugin in self.plugins:
            if type(self.plugins[plugin]).__name__ == 'FinalSmooth' and \
                self.plugins[plugin].params['Active']:
                final_blur = self.plugins[plugin].params['Blur'] * 255
                final_threshold = self.plugins[plugin].params['Threshold'] * 255
                print("Final Smooth (Blur value)", final_blur)

        # If there are masks or interps avaliable
        if (len(self._inter_msk) > 0) or (len(self._inter_int) > 0):
            # Adjust mask for different projections (zoom levels)
            final_blur = int(final_blur * self.matrix[0, 0])

            # merge all the masks together store in self._out[self.config.msk]
            self.combine_masks(w, 
                               h, 
                               final_threshold=final_threshold, 
                               final_blur=final_blur, 
                               keep_outline=keep_outline)

            # Create rgb image with the mask 'cut out' from it
            img_cutout = cv2.bitwise_and(self._out[self.config.msk], img_out_rgb)

            # Add in the background from the cutout
            if keep_background >= 0.05:
                alpha = (1.0 - keep_background)
                beta = keep_background
                img_result = cv2.addWeighted(img_cutout, alpha, img_out_rgb, beta, 0)
            else:
                img_result = img_cutout

            # Add in the keep mask outline
            if keep_outline:
                img_result = img_result | self._out[self.config.KOL]

            # TODO - How to deal with multiple interps.
            # Probably need to have a plugin to deal with precedence and 
            # perhaps even majority voting for 'automatic' techniques.
            # in the mean time - Add some interp right here, right now
            if len(self._inter_int) > 0 and show_interp >= 0.05:
                for plugin in self.plugins:
                    active = self.plugins[plugin].params.get("Active", False)
                    type_interp = self.plugins[plugin].type_interp
                    type_draw = self.plugins[plugin].type_draw
                    # plugin can exist but not have a interp layer so we need a check
                    int_exists = True if plugin in self._inter_int else False

                    if int_exists and active and type_interp and (not type_draw):
                        img_interp = cv2.warpAffine(self._inter_int[plugin], 
                                            self.matrix, 
                                            (w, h),
                                            flags=self.interpolations[self.config.interpolation_type])

                        alpha = (1.0 - show_interp)
                        beta = show_interp
                        img_result = cv2.addWeighted(img_result, alpha, img_interp, beta, 0)

                # If there is a draw interp merge into masks 
                # Must be done after apply other plugins to give high precedence.
                for plugin in self.plugins:
                    active = self.plugins[plugin].params.get("Active", False)
                    type_interp = self.plugins[plugin].type_interp
                    type_draw = self.plugins[plugin].type_draw

                    # TODO 
                    # instead of if self.config.drwint generated, we know this layer exists 

                    generated = self.plugins[plugin].id in self._inter_int
                    if active and type_draw and generated and type_interp:
                        # TODO
                        # In future this should not be a addweighted 
                        # but a replace if pixel value is not 'undefined' / "don't care" class
                        # something like np.where etc etc
                        img_interp = cv2.warpAffine(self._inter_int[self.plugins[plugin].id], 
                                            self.matrix, 
                                            (w, h),
                                            flags=self.interpolations[self.config.interpolation_type])

                        alpha = (1.0 - show_interp)
                        beta = show_interp
                        img_result = cv2.addWeighted(img_result, alpha, img_interp, beta, 0)
        else:
            img_result = img_out_rgb

        # Finally add in any temp. UI elements
        img_result = self.update_ui(img=img_result, x=mouse_x, y=mouse_y)
        
        return img_result
    
    def update_double(
            self, 
            w, 
            h,
            keep_background=0.5,
            show_interp=0.5,
            keep_outline=True,
            mouse_x=None,
            mouse_y=None,
        ):
        
        self.view_width, self.view_height = float(w), float(h)
  
        img_out_rgb = self.update_single(
            w, 
            h, 
            keep_background=keep_background,
            show_interp=show_interp,
            keep_outline=keep_outline,
            mouse_x=mouse_x,
            mouse_y=mouse_y,
        )

        img_secondary = cv2.warpAffine(self._in[self.config.dip], 
                                        self.matrix, 
                                        (w, h),
                                        flags=self.interpolations[self.config.interpolation_type])

        return img_out_rgb, img_secondary

    def update_ui(self, img, x=None,  y=None):
        # INFUTURE:
        # • Also add colour to the circle if the user is doing interp.
        # Add a draw_circle_size preview so user knows what they are about to 
        # do before they start drawing - without this it is difficult to get 
        # a feel for what will happen

        # If there are ui layers add them - for example for mouse over
        # if ui exists
        if len(self._inter_ui) > 0:
            for layer in self._inter_ui:

                # Warp the layer before applying it to img
                w, h = int(self.view_width), int(self.view_height)
                img_layer = cv2.warpAffine(self._inter_ui[layer], 
                                           self.matrix, 
                                           (w, h),
                                           flags=self.interpolations[self.config.interpolation_type])

                blank_color = self.config.blank_mouse_over
                img[:,:,0] = np.where(img_layer[:,:,0] != blank_color[0], img_layer[:,:,0], img[:,:,0])
                img[:,:,1] = np.where(img_layer[:,:,1] != blank_color[1], img_layer[:,:,1], img[:,:,1])
                img[:,:,2] = np.where(img_layer[:,:,2] != blank_color[2], img_layer[:,:,2], img[:,:,2])

            # TODO
            # Does the inter_ui need to be deleted now? try and see
            self._inter_ui = {}


        # Add mouse circle if there is a size 
        if self.draw_circle_size and x and y:
            # Inner circle
            img = cv2.circle(
                img, 
                (x, y),
                radius=self.draw_circle_size//2,
                color=(196, 196, 196),
                thickness=2,
                lineType=cv2.LINE_AA
            )
            # Outer Circle
            img = cv2.circle(
                img, 
                (x, y),
                radius=self.draw_circle_size//2,
                color=(32, 32, 32),
                thickness=1,
                lineType=cv2.LINE_AA
            )
        
        return img
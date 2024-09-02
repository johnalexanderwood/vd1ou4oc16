# The module contains the Filter classes for the RockClean application.

import copy
import cv2
import numpy as np
import sys


class Filters:
    def __init__(self):
        self.cache = {}
        self.CACHE_LIMIT = 80

    def clear_cache(self):
        self.cache = {}

    def limit_cache(self):
        # Simple solution to stop cache getting too large, total stall of pipeline
        if len(self.cache) > self.CACHE_LIMIT:
            self.cache = {}

    # Modified from here - https: // wiki.python.org / moin / PythonDecoratorLibrary  # Memoize
    def by_hsv_colors(self, *args):

        # Check the cache has not go too large
        self.limit_cache()

        # Working: Arguments to string
        key = ''
        for arg in args[1:]:
            key += str(arg)

        if key in self.cache:
            #print(f'Cache Hit: Cache Length {len(self.cache)}, Size KB {sys.getsizeof(self.cache) / 1024}')
            return self.cache[key]
        else:
            value = self.simple_by_hsv_colors(*args)
            self.cache[key] = value
            #print(f'Size of value being added to cache: {sys.getsizeof(value)}')
            #print(f'Cache Miss: Cache Length {len(self.cache)}. , Size KB {sys.getsizeof(self.cache) / 1024}')
            return value

    def edbat_mask(self, img_mask, erode, dilate, blur, threshold) -> np.ndarray:
        """Function to process mask with Erode, Dilate, Blur and Threshold"""
        kernel = np.ones((3, 3), np.uint8)

        # Do some qc of the blur
        blur = int(blur)
        if (blur % 2) == 0:
            blur -= 1

        if erode > 0:
            img_mask = cv2.erode(img_mask, kernel, iterations=erode)
        if dilate > 0:
            img_mask = cv2.dilate(img_mask, kernel, iterations=dilate)
        if blur > 0:
            img_mask = cv2.GaussianBlur(img_mask, (blur, blur), 0)

        ret, img_mask = cv2.threshold(img_mask, threshold, 255, cv2.THRESH_BINARY)

        return img_mask

    def simple_by_hsv_colors(self, img, type, colours, thresholds, edbats, invert_output, convert_RGB2HSV=False):
        """Function to mask one or more colours by HSV value then process result
        with edbat_mask"""

        img_result_final = np.zeros(img.shape[0:2], np.uint8)
        img_results = []

        if convert_RGB2HSV:
            img_hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
        else:
            img_hsv = img


        for hsv, threshold, EDBaT in zip(colours, thresholds, edbats):
            img_result_ = np.zeros(img.shape[0:2], np.uint8)

            # Check if thresholds are less than 255
            for i, t in enumerate(threshold):
                if t > 255:
                    threshold[i] = 255
                if t < 0:
                    threshold[i] = 0

            # Ignore hues greater than 180
            if hsv[0] > 180:
                print("Error: Hue value greater than 180 supplied")
                hsv[0] = 180

            # Create mask for that hue's pixels
            lower = (hsv[0] - threshold[0], hsv[1] - threshold[1], hsv[2] - threshold[2])
            upper = (hsv[0] + threshold[0], hsv[1] + threshold[1], hsv[2] + threshold[2])
            # lower = np.array((lower), dtype=np.uint8)
            # upper = np.array((upper), dtype=np.uint8)
            img_mask = cv2.inRange(img_hsv, lower, upper)

            # Or the results up, so new filters get chained together
            img_result_ = cv2.bitwise_or(img_mask, img_result_)

            # Catch if lower or upper need to wrap round,
            # IE the Red edge case
            # Thus need to run the inRange and combine functions twice
            if lower[0] < 0:
                # Subtract from upper and run again
                lower = (180 + lower[0], hsv[1] - threshold[1], hsv[2] - threshold[2])
                upper = (180, hsv[1] + threshold[1], hsv[2] + threshold[2])

                img_mask = cv2.inRange(img_hsv, lower, upper)

                # Then combine with the overall result
                img_result_ = cv2.bitwise_or(img_mask, img_result_)
            elif upper[0] > 180:
                # Add to the lower and run again
                lower = (0, hsv[1] - threshold[1], hsv[2] - threshold[2])
                upper = (0 + (lower[0] - 255), hsv[1] + threshold[1], hsv[2] + threshold[2])
                # print('second lower and uppers pass', lower, upper)

                img_mask = cv2.inRange(img_hsv, lower, upper)

                # Then combine with the overall result
                img_result_ = cv2.bitwise_or(img_mask, img_result_)

            img_result_ = self.edbat_mask(img_result_, EDBaT[0], EDBaT[1], EDBaT[2], EDBaT[3])

            img_results.append(copy.deepcopy(img_result_))

        # Loop through all the images and create a final filtered image
        for img in img_results:
            img_result_final = cv2.bitwise_or(img, img_result_final)

        if invert_output:
            img_result_final = cv2.bitwise_not(img_result_final)

        return img_result_final

    def combine_masks_and(self, image_1, image_2, edbat, invert_output=False):
        image_result = np.zeros(image_1.shape, np.uint8)

        # Check size of images
        if image_1.shape != image_2.shape:
            print("combine_masks_and: Error Shapes of input images don't match")
        else:
            image_result = cv2.bitwise_and(image_1, image_2)

        image_result = self.edbat_mask(image_result, edbat[0], edbat[1], edbat[2], edbat[3])

        if invert_output:
            image_result = cv2.bitwise_not(image_result)

        return image_result

    def combine_masks_or(self, image_1, image_2, edbat, invert_output=False):
        image_result = np.zeros(image_1.shape, np.uint8)

        # Check size of images
        if image_1.shape != image_2.shape:
            print("combine_masks_or: Error Shapes of input images don't match")
        else:
            image_result = cv2.bitwise_or(image_1, image_2)

        image_result = self.edbat_mask(image_result, edbat[0], edbat[1], edbat[2], edbat[3])

        if invert_output:
            image_result = cv2.bitwise_not(image_result)

        return image_result

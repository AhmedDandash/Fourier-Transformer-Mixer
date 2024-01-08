
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPixmap, QPainter
from PyQt6.QtCore import Qt
from PIL import Image, ImageQt, ImageEnhance
import copy
import numpy as np




class ImageViewport(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        # keep track of mini figure size.
        self.original_img = None
        self.resized_img = None
        self.image_area = None
        self.viewport_image_ind = None  # (brightness, contrast)
        self.brightness = 0
        self.contrast = 0
        self.last_x = 0
        self.last_y = 0
        self.main_window = main_window
        self.original_brightness = 0  # Store the original brightness value
        self.original_contrast = 0  # Store the original contrast value

    def set_image(self, image_path):
     
            # Graysclae image 
            image = Image.open(image_path).convert('L')

            self.original_img = image
            # To save all complex and all copies in orinal img 
            self.resized_img = copy.deepcopy(self.original_img)  

            self.image_area = float(self.original_img.height * self.original_img.width)
            self.main_window.images_areas[self.viewport_image_ind] = self.image_area
            self.reducing_size()
               # Save the original brightness value
            self.original_brightness = 0
            self.original_contrast = 0
            self.adjust_brightness_contrast()
            self.update_display()

    def update_display(self):
   
        if self.original_img:
            self.repaint()

    def paintEvent(self, event):
        super().paintEvent(event) #QWidget

        if self.original_img:
            with QPainter(self) as painter_img:

                # adjust brightness, contrast, and resize the image
                self.adjust_brightness_contrast()
                resized_img = self.resized_img.resize((self.width(), self.height()))
                # Draw the image on the widget
                pixmap = QPixmap.fromImage(ImageQt.ImageQt(resized_img))
                painter_img.drawPixmap(0, 0, pixmap)

    def mouseMoveEvent(self, event):
        if self.resized_img and event.buttons() == Qt.RightButton:
            # Calculate the displacement from the last mouse position
            dx = event.x() - self.last_x
            dy = event.y() - self.last_y

            # Update brightness based on horizontal movement
            self.brightness += dx
            # Update contrast based on vertical movement
            self.contrast += dy

            # Clamp brightness and contrast values to valid ranges
            self.brightness = max(-255, min(255, self.brightness))
            self.contrast = max(-255, min(255, self.contrast))

            # Update the image with adjusted brightness and contrast
            self.adjust_brightness_contrast()
            self.main_window.components_ports[self.viewport_image_ind].update_FT_components(
            )
            # Update the display\
            self.update_display()
        # Save the current mouse position for the next event
            self.last_x = event.x()
            self.last_y = event.y()
        else:
            event.accept()
            return
       
   

    def mousePressEvent(self, event):
 
        # Save the initial mouse position when the mouse is pressed
        self.last_x = event.x()
        self.last_y = event.y()
        if event.button() == Qt.RightButton:
            # Reset both brightness and contrast to original values
            self.brightness = self.original_brightness
            self.contrast = self.original_contrast
            # Adjust brightness and contrast to reset to the original image
            self.adjust_brightness_contrast()
            self.update_display()

        # Call the base class implementation
        super().mousePressEvent(event)

    def reducing_size(self):
        #make all sizes of the images same make make it as the smallest one.
        min_area = float(min(self.main_window.images_areas))
        if min_area < self.image_area:
            index_of_interest = np.where(self.main_window.images_areas == min_area)[0][0]  
            template_image = self.main_window.image_ports[index_of_interest].original_img
            self.resized_img = self.resized_img.resize(
                (template_image.width, template_image.height))
        elif min_area == self.image_area:
            self.main_window.define_image_size(self.viewport_image_ind)

    def adjust_brightness_contrast(self):
     
        # Adjust brightness
        brightness_factor = (self.brightness + 255) / 255.0
        brightness_enhancer = ImageEnhance.Brightness(
            self.original_img.resize(self.resized_img.size))
        img_with_brightness_adjusted = brightness_enhancer.enhance(
            brightness_factor)

        # Adjust contrast
        contrast_factor = (self.contrast + 127) / 127.0
        contrast_enhancer = ImageEnhance.Contrast(img_with_brightness_adjusted)
        self.resized_img = contrast_enhancer.enhance(contrast_factor)

    def image_parameters(self, path):

        # images indices by openeing order
        order = self.main_window.open_order

        # latest opened image index
        current = order[-1]

        self.main_window.image_ports[current].set_image(path)

        # set some attributes of the Image
        component = self.main_window.ui_image_combo_boxes[current].currentText(
        )

        self.main_window.components[str(current+1)] = component

        self.main_window.ui_vertical_sliders[current].setValue(100)

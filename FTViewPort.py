from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPixmap, QPainter
from PIL import Image, ImageQt
from PyQt6.QtGui import QPainter, QBrush, QPen
from PyQt6.QtCore import Qt, QRect, QTimer,  QEvent
import numpy as np
from scipy.fft import fft2, fftshift


class FTViewPort(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.viewport_FT_ind = None  # the index of the components view port
        # as widget object, Used for selecting different FT components and handling combo box events.
        self.combo_box = None
        # Used to access and interact with other components of the main application.
        self.main_window = main_window
        self.curr_component_name = None
        self.pre_widget_dim = None  # keep track the previous dimension of the viewport
        self.image_data = None  # Used for computing FT components
        # Used to access the pixel data of the currently selected FT component.
        self.component_data = None

        self.reactivate_drawing_events()

        # Used to cache FT component images for efficient display
        self.ft_components_images = {}
        # Used to cache FT component data for further processing.
        self.ft_components = {}
        # Used for adjusting weights during the mixing process.
        self.weight_slider = None
        # Used for displaying the original image and updating the display.
        self.original_img = None
        # Used for displaying the image with adjusted dimensions.
        self.resized_img = None
        self.press_pos = None  # The left-upper point of the rectangle
        self.release_pos = None  # the bottom-right corner of the rectangle
        # the press point at which rectangle dragging started.
        self.drag_point = None

        self.drawRect = False  # Used to control the drawing state.
        # Used to control the state of holding a drawn rectangle.
        self.holdRect = False
        # Used to control the state of moving a drawn rectangle.
        self.move_active = False
        # Stores the coordinates and dimensions of the rectangle.
        self.current_rect = QRect()

    def set_image(self):
                  # Get the image for the current component
            image = self.ft_components_images[self.curr_component_name]
            # Set the original image
            self.original_img = image
            # Update the display
            self.update_display()

    def update_display(self):
        if self.original_img:
            self.repaint()

    def paintEvent(self, event):
        super().paintEvent(event)

        # Check if there is an original image
        if self.original_img:
            with QPainter(self) as painter_comp:
                # Resize the original image to match the size of the widget
                self.resized_img = self.original_img.resize(
                    (self.width(), self.height()))
                # Convert the resized image to QPixmap
                pixmap = QPixmap.fromImage(
                    ImageQt.ImageQt(self.resized_img))

                # Draw the pixmap on the widget
                painter_comp.drawPixmap(0, 0, pixmap)

        # Check if either holdRect or drawRect is True
        if self.holdRect or self.drawRect:
            self.draw_rectangle()

        self.currently_painting = False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        map_to = (self.width(), self.height())
        if self.original_img != None:
            if self.holdRect and self.press_pos:  # check of existence of a rectangle
                position_list = [(self.press_pos.x(), self.press_pos.y()),
                                 (self.release_pos.x(), self.release_pos.y())]

                mapped_position_list = self.map_rectangle(
                    # get the mapped points of the rectangle.
                    position_list, self.pre_widget_dim, map_to)
                start_point, end_point = mapped_position_list
                # recreate the rectangle
                self.current_rect = QRect(
                    start_point[0], start_point[1], end_point[0] - start_point[0], end_point[1] - start_point[1])
                self.press_pos, self.release_pos = self.current_rect.topLeft(
                ), self.current_rect.bottomRight()
            # update the previous size of widget
        self.pre_widget_dim = (self.width(), self.height())

    def update_FT_components(self):
        self.image_data = np.array(
            self.main_window.image_ports[self.viewport_FT_ind].resized_img)

        self.calculate_fft()
        self.handle_image_combo_boxes_selection()

    def handle_image_combo_boxes_selection(self):

        self.curr_component_name = self.combo_box.currentText()  # note a None object why?
        if self.ft_components_images and self.curr_component_name not in [None, ""]:
            self.component_data = self.ft_components[self.curr_component_name]
            self.main_window.components[str(
                self.viewport_FT_ind + 1)] = self.curr_component_name
            self.set_image()

    def draw_rectangle(self):
 
        with QPainter(self) as painter_rect:
            painter_rect.setPen(QPen(Qt.blue, 2, Qt.SolidLine))
            painter_rect.setBrush(QBrush(Qt.blue, Qt.DiagCrossPattern))
            painter_rect.drawRect(self.current_rect)

    def draw_mousePressEvent(self, event):
  
        if event.button() == Qt.MouseButton.LeftButton:
            self.press_pos = event.position()
            self.current_rect.setTopLeft(self.press_pos.toPoint())
            self.current_rect.setBottomRight(self.press_pos.toPoint())
            self.drawRect = True

    def draw_mouseMoveEvent(self, event):
        if self.drawRect:
            self.current_rect.setBottomRight(event.position().toPoint())
            self.update_display()
        else:
            event.accept()
            return

    def draw_mouseReleaseEvent(self, event):

        if event.button() == Qt.MouseButton.LeftButton:
            self.release_pos = event.position()
            self.main_window.mixer.generalize_rectangle(
                self.viewport_FT_ind)
            self.drawRect = False

    def move_mousePressEvent(self, event):

        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_point = event.position()
            # Check if the press position is inside the current rectangle
            if self.current_rect.contains(self.drag_point.toPoint()):
                self.move_active = True

    def move_mouseReleaseEvent(self, event):

        if event.button() == Qt.MouseButton.LeftButton:
            self.release_pos = self.current_rect.bottomRight()
            self.press_pos = self.current_rect.topLeft()
            self.move_active = False
            self.drag_point = None

    def move_mouseMoveEvent(self, event):

        if self.move_active and self.drag_point != None:
            # Calculate the offset to move the rectangle
            offset = event.position() - self.drag_point

            # Calculate the new position of the top-left corner
            new_top_left = self.current_rect.topLeft() + offset.toPoint()

            # Ensure the new position stays within the original image boundaries
            if self.rectangleborders(new_top_left):
                self.current_rect.translate(offset.toPoint())
                self.drag_point = event.position()
                self.update_display()
        else:
            event.accept()
            return

    def map_rectangle(self, position_list, map_from, map_to):
        mapped_up_position_list = []
        for position in position_list:
            actual_x_value = round(self.main_window.map_value(
                position[0], 0, map_from[0], 0, map_to[0]))
            actual_y_value = round(self.main_window.map_value(
                position[1], 0, map_from[1], 0, map_to[1]))
            mapped_up_position_list.append((actual_x_value, actual_y_value))
        return mapped_up_position_list

    def rectangleborders(self, top_left):
        # bt- check if the rectange is in the widget or nor.
        return self.rect().contains(QRect(top_left, self.current_rect.size()))

    def deactivate_drawing_events(self):
        self.holdRect = True
        self.move_active = True
        self.mousePressEvent = self.move_mousePressEvent
        self.mouseMoveEvent = self.move_mouseMoveEvent
        self.mouseReleaseEvent = self.move_mouseReleaseEvent

    def reactivate_drawing_events(self):
        self.holdRect = False
        self.move_active = False
        self.mousePressEvent = self.draw_mousePressEvent
        self.mouseMoveEvent = self.draw_mouseMoveEvent
        self.mouseReleaseEvent = self.draw_mouseReleaseEvent

    def calculate_fft(self):

        fft = fft2(self.image_data)

        # to bring the low-frequency components to the center of the image for better interpretation.
        fft_shifted = fftshift(fft)

        # Compute the magnitude of the spectrum
        mag = np.abs(fft_shifted)
        mag_log = 15 * np.log(mag + 1e-10).astype(np.uint8)

        # Compute the phase of the spectrum
        phase = np.angle(fft_shifted).astype(np.uint8)

        # Compute the real and imaginary components
        real = 15 * np.log(np.abs(np.real(fft_shifted)) +
                           1e-10).astype(np.uint8)
        imaginary = fft_shifted.imag.astype(np.uint8)

        # Store the results as images
        self.ft_components_images['FT Magnitude'] = Image.fromarray(
            mag_log, mode="L")
        self.ft_components_images['FT Phase'] = Image.fromarray(
            phase, mode='L')
        self.ft_components_images["FT Real"] = Image.fromarray(real, mode='L')
        self.ft_components_images["FT Imaginary"] = Image.fromarray(
            imaginary, mode='L')

        # Store the numerical components
        self.ft_components['FT Magnitude'] = np.abs(fft_shifted)
        self.ft_components['FT Phase'] = np.angle(fft_shifted)
        self.ft_components['FT Real'] = fft_shifted.real
        self.ft_components['FT Imaginary'] = fft_shifted.imag

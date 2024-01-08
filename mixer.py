from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QWidget,
)

from PIL import Image

from PyQt6.QtCore import QRect

from PyQt6 import QtWidgets
# Placeholder for FT-related functionalities
import numpy as np
from scipy.fft import ifft2, fftshift, ifftshift
from PyQt6.QtWidgets import QWidget
class ImageMixer(QWidget):
    def __init__(self, main_window, parent=None):
        # Initialize the class
        super().__init__(parent)

        # Initialize instance variables
        self.mix_image = None
        self.main_window = main_window
        self.fft2_output = []
        self.mixing_comp = []
        self.weight_value = np.repeat(1.0, 4)
        self.selection_mode = 1
        self.output = 1        # the index of the FTviewport at which the mixing begins
        self.higher_precedence_ft_component = None
        self.resetallarrays()

        # Connect radio button toggled signals to corresponding handlers
        self.main_window.ui.radioButton_In.toggled.connect(
            self.handle_radio_button_toggled)
        self.main_window.ui.radioButton_Out.toggled.connect(
            self.handle_radio_button_toggled)

        # Connect output radio button toggled signals to corresponding handlers
        self.main_window.ui.radioButton1.toggled.connect(
            self.handle_out_radio_button_toggled)
        self.main_window.ui.radioButton2.toggled.connect(
            self.handle_out_radio_button_toggled)

        # Set default radio button states
        self.main_window.ui.radioButton_In.setChecked(True)
        self.main_window.ui.radioButton1.setChecked(True)

    def collect_piece_data(self):
        for ind in range(len(self.piece)):
            # meaning that there is a region selected.
            if self.main_window.image_ports[ind].original_img != None:
                port = self.main_window.components_ports[ind]
                if port.holdRect:
                    selection_matrix = self.get_area_selected(ind)
                    curr_piece = selection_matrix * \
                        port.component_data
                else:
                    curr_piece = port.component_data

                self.piece[str(ind)] = curr_piece

    def get_area_selected(self, ind):
           # Get information about the specific port
        port = self.main_window.components_ports[ind]
            # Get the original and resized image sizes
        map_up_size = port.original_img.size
        port_dim = port.resized_img.size
            # Create a list of two positions: press and release positions
        position_list = [(port.press_pos.x(), port.press_pos.y()),
                         (port.release_pos.x(), port.release_pos.y())]
            # Map the position list from the resized image to the original image
        mapped_up_position_list = port.map_rectangle(
            position_list, port_dim, map_up_size)
            # Initialize the selection matrix based on the selection mode
        if self.selection_mode:
            selection_matrix = np.zeros_like(port.component_data)
        else:
            selection_matrix = np.ones_like(port.component_data)

        # y_iteration
        for i in range(mapped_up_position_list[0][1], round(mapped_up_position_list[1][1] + 1)):
            # X_iteration
            for j in range(mapped_up_position_list[0][0], mapped_up_position_list[1][0] + 1):
                if self.selection_mode:  # 1 --> inner
                    selection_matrix[i, j] = 1
                else:  # outer
                    selection_matrix[i, j] = 0
        return selection_matrix

    def generalize_rectangle(self, ind):
        if self.higher_precedence_ft_component is None:
            self.higher_precedence_ft_component = ind
            # the object of position is the same as object of data
            # Iterate through components_ports
        for i, port in enumerate(self.main_window.components_ports):
            # Get the image associated with the current port
            image = self.main_window.image_ports[i]
            if image.original_img is not None:
                port.current_rect = QRect(self.main_window.components_ports[self.higher_precedence_ft_component].current_rect)
                port.press_pos, port.release_pos = port.current_rect.topLeft(
                ), port.current_rect.bottomRight()

                port.deactivate_drawing_events()
                port.set_image()

    def mix_images(self):

      # arrange the pairs to determine the mixing order
        mixing_choices = self.mode_choice()

        # Compose the complex output for the first pair
        self.fft2_output = []
        self.fft2_output = self.compose_complex(mixing_choices)

        # Calculate the mixed image using inverse Fourier transform
        self.mixed_image = np.real(ifft2(self.fft2_output)).astype(np.uint8)

        # Create an image object from the mixed image array
        self.mixed_image = Image.fromarray(self.mixed_image, mode="L")

        # Set the mixed image as the output image in the main window
        self.main_window.out_ports[self.output].set_image(self.mixed_image)

        # Deselect any selected items in the main window
        self.resetallarrays()

    def mode_choice(self):
        if self.main_window.curr_mode == "Mag and Phase":
            mixing_choices = {"FT Magnitude": [], "FT Phase": []}
        else:
            mixing_choices = {"FT Real": [], "FT Imaginary": []}
            
        for i, combo in enumerate(self.main_window.ui_image_combo_boxes):
            if np.any(self.piece[str(i)]):
                mixing_choices[combo.currentText()].append(i)
        return mixing_choices

    def compose_complex(self, mixing_choices):  
        if "FT Magnitude" in mixing_choices:
            mag_indices = mixing_choices["FT Magnitude"]
            phase_indices = mixing_choices["FT Phase"]
            total_mag = self.accumulate(mag_indices)
            total_phase = self.accumulate(phase_indices)
            complex_numbers = total_mag * np.exp(
                1j * total_phase)
        else:
            real_indices = mixing_choices["FT Real"]
            img_indices = mixing_choices["FT Imaginary"]
            total_real = self.accumulate(real_indices)
            total_imaginary = self.accumulate(img_indices)
            complex_numbers = total_real + \
                1j * total_imaginary

        return ifftshift(complex_numbers)

    def accumulate(self, indices):
        output_size = max(self.piece.values(), key=len).shape
        product_output = np.zeros(output_size, dtype=float)
        for index in indices:
            product_output += (self.piece[str(index)] *self.weight_value[index])
        return product_output

    def handle_radio_button_toggled(self):
        if self.main_window.ui.radioButton_In.isChecked():
            # If the "In" radio button is checked, set the selection mode to 1
            self.selection_mode = 1
        elif self.main_window.ui.radioButton_Out.isChecked():
            # If the "Out" radio button is checked, set the selection mode to 0
            self.selection_mode = 0

    def handle_out_radio_button_toggled(self):
        if self.main_window.ui.radioButton1.isChecked():
            # Set output to 0 if radioButton1 is checked
            self.output = 0
        elif self.main_window.ui.radioButton2.isChecked():
            # Set output to 1 if radioButton2 is checked
            self.output = 1

    def handle_weight_sliders(self):

        # Get the slider that triggered the event
        slider = self.sender()

        # Find the index of the slider in the list of vertical sliders
        slider_ind = self.main_window.ui_vertical_sliders.index(slider)

        # Calculate the new weight value based on the slider value and the previous weight reference
        new_weight_value = slider.value() / 100

        # Update the weight value with the calculated new value
        self.weight_value[slider_ind] = new_weight_value

    def resetallarrays(self):
        self.piece = {
            "0": np.array([]),
            "1": np.array([]),
            "2": np.array([]),
            "3": np.array([])
        }

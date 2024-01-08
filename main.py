from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QVBoxLayout,  QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6 import QtWidgets, uic
import numpy as np
import sys
import qdarkstyle
from PyQt6.QtCore import Qt, QRect
import sys
from imageViewPort import ImageViewport
from FTViewPort import FTViewPort
from OutViewPort import OutViewPort
from mixer import ImageMixer
from ThreadingClass import WorkerSignals, WorkerThread

class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.init_ui()

    def init_ui(self):
       
        # Load the UI Page
        self.ui = uic.loadUi('Mainwindow.ui', self)
        self.setWindowTitle("Image Mixer")
        self.setWindowIcon(QIcon("icons/mixer.png"))
        self.image_ports = []
        self.components_ports = []
        self.images_areas = np.repeat(np.inf, 4)  # initialized
        self.out_ports = []
        self.open_order = []
        self.min_width = None
        self.min_height = None
        self.curr_mode = None
        self.worker_thread = None
        self.components = {"1": '', "2": '', '3': '', '4': ''}
        self.ui.output1_port.resize(
            self.ui.original1.width(), self.ui.original1.height())
        # mixer and its connection line
        self.mixer = ImageMixer(self)
        self.ui.mixxer.clicked.connect(self.start_thread)
        self.ui.Deselect.clicked.connect(self.deselect)
        self.load_ui_elements()
        self.showFullScreen()
        self.ui.keyPressEvent = self.keyPressEvent

        self.worker_signals = WorkerSignals()

    def show_error_message(self, message):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("Error")
        msg_box.setText(message)
        msg_box.exec()

    def deselect(self):
        for comp in self.components_ports:
            self.mixer.higher_precedence_ft_component = None
            if comp.original_img != None:
                comp.press_pos = None
                comp.release_pos = None
                comp.current_rect = QRect()
                comp.reactivate_drawing_events()
                comp.update_display()

    def start_thread(self):
        if len(self.open_order) != 1:
            if self.worker_thread and self.worker_thread.is_alive():
                self.worker_thread.cancel()
               
            self.worker_signals.canceled.clear()
            self.worker_thread = WorkerThread(
                5, self.worker_signals, self)
            self.worker_thread.start()
        else:
            self.show_error_message('Please choose valid pairs')

            return

    def map_value(self, value, lower_range, upper_range, lower_range_new, upper_range_new):
       

        mapped_value = ((value - lower_range) * (upper_range_new - lower_range_new) /
                        (upper_range - lower_range)) + lower_range_new
        return mapped_value

    def define_image_size(self, template_image_ind):
      
        for i, image in enumerate(self.image_ports):
            # Check if the image is not the template and has an original image
            if i != template_image_ind and image.original_img is not None:
                # Get the template image
                template_image = self.image_ports[template_image_ind].resized_img
                #Resize the current iage resized img to match the template image data dimensions 
                image.resized_img = image.resized_img.resize(
                    (template_image.width, template_image.height))
                image.update_display()
                # Update the Fourier Transform components for the corresponding component port
                self.components_ports[i].update_FT_components()

    def keyPressEvent(self, event):
       
        # Handle key events, for example, pressing ESC to exit full screen
        if event.key() == Qt.Key.Key_Escape:
            self.showNormal()  # Show the window in normal size
        else:
            super().keyPressEvent(event)

    def load_ui_elements(self):
       
        # Define lists of original UI view ports, output ports, component view ports, image combo boxes, mixing combo boxes, and vertical sliders
        self.ui_view_ports = [self.ui.original1, self.ui.original2,
                              self.ui.original3, self.ui.original4]
        self.ui_out_ports = [self.ui.output1_port, self.ui.output2_port]
        self.ui_view_ports_comp = [
            self.ui.component_image1, self.ui.component_image2, self.ui.component_image3, self.ui.component_image4]
        self.ui_image_combo_boxes = [
            self.ui.combo1, self.ui.combo2, self.ui.combo3, self.ui.combo4]

        self.ui_vertical_sliders = [
            self.ui.Slider_weight1, self.ui.Slider_weight2, self.ui.Slider_weight3, self.ui.Slider_weight4]
        self.ui.vertical_layouts = [
            (self.ui.verticalLayout, self.verticalLayout_2), (self.ui.verticalLayout_10,
                                                              self.ui.verticalLayout_11), (self.ui.verticalLayout_5, self.ui.verticalLayout_6),
            (self.ui.verticalLayout_13, self.ui.verticalLayout_14)
        ]

        self.ui_modes = [self.ui.mode1, self.ui.mode2]

        for mode in self.ui_modes:
            mode.clicked.connect(self.radio_button_mode_clicked)

        self.ui_modes[0].click()

        self.out_vertical_layout = [
            self.ui.verticalLayout_OP1, self.ui.verticalLayout_OP2]
        # Create image viewports and bind browse_image function to the event
        self.image_ports.extend([
            self.create_image_viewport(self.ui_view_ports[i], lambda event, index=i: self.browse_image(event, index)) for i in range(4)])

        # Create FT viewports
        self.components_ports.extend([self.create_FT_viewport(
            self.ui_view_ports_comp[i]) for i in range(4)])

        # Create output viewports
        self.out_ports.extend([self.create_output_viewport(
            self.ui_out_ports[i]) for i in range(2)])

        # Loop through each combo box and associated components_ports
        for i, combo_box in enumerate(self.ui_image_combo_boxes):
            # Set the combo box and weight slider for the corresponding components_port
            self.components_ports[i].combo_box = combo_box
            self.components_ports[i].weight_slider = self.ui_vertical_sliders[i]

            # Set the minimum and maximum values for the weight slider
            self.ui_vertical_sliders[i].setMinimum(1)
            self.ui_vertical_sliders[i].setMaximum(100)

            # Connect the valueChanged signal of the weight slider to the handle_weight_sliders method of the mixer
            self.ui_vertical_sliders[i].valueChanged.connect(
                self.mixer.handle_weight_sliders)

            # Connect the currentIndexChanged signal of the combo box to the handle_image_combo_boxes_selection method of the components_port
            combo_box.currentIndexChanged.connect(
                self.components_ports[i].handle_image_combo_boxes_selection)

    def radio_button_mode_clicked(self):
        sender = self.sender()  # Get the radio button that triggered the signal
        self.curr_mode = sender.text()
        # Add items to the combo box and set the current index to 0
        for i, combo_box in enumerate(self.ui_image_combo_boxes):
            combo_box.clear()
            if self.curr_mode == "Mag and Phase":
                combo_box.addItems(
                    ["FT Magnitude", "FT Phase"])
            else:
                combo_box.addItems(
                    ["FT Real", "FT Imaginary"])

            if self.components_ports != []:
                print("update ft components")
                curr_port = self.components_ports[i]
                if self.worker_thread:
                    self.worker_thread.cancel()
                    self.worker_signals.canceled.clear()
                    self.deselect()
                if curr_port.original_img != None:
                    curr_port.update_FT_components()

            combo_box.setCurrentIndex(0)

    def browse_image(self, event, index: int):
        file_filter = "Raw Data (*.png *.jpg *.jpeg *.jfif)"
        image_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            None, 'Open Signal File', './', filter=file_filter)

        if image_path and 0 <= index < len(self.image_ports):
            image_port = self.image_ports[index]
            if index not in self.open_order:
                self.open_order.append(index)
            else:
                # swap ,and make the one we open the last one
                self.open_order[-1], self.open_order[self.open_order.index(
                    index)] = self.open_order[self.open_order.index(index)], self.open_order[-1]

            self.handling_image(index, image_port, image_path)

    def handling_image(self, index, image_port, image_path):
        # Update the viewport image index
        image_port.viewport_image_ind = index

        # Update the FT index of the component port
        self.components_ports[index].viewport_FT_ind = index

        # Update the image parameters
        image_port.image_parameters(image_path)

        # store the loading initial size of the component viewport
        self.components_ports[index].pre_widget_dim = (
            self.components_ports[index].width(), self.components_ports[index].height())

        # Update the FT components of the component port
        self.components_ports[index].update_FT_components()


    def create_viewport(self, parent, viewport_class, mouse_double_click_event_handler=None):
        new_port = viewport_class(self)
        layout = QVBoxLayout(parent)
        layout.addWidget(new_port)

        if mouse_double_click_event_handler:
            new_port.mouseDoubleClickEvent = mouse_double_click_event_handler

        return new_port

    def create_image_viewport(self, parent, mouse_double_click_event_handler):
        return self.create_viewport(parent, ImageViewport, mouse_double_click_event_handler)

    def create_FT_viewport(self, parent):
        return self.create_viewport(parent, FTViewPort)

    def create_output_viewport(self, parent):
        return self.create_viewport(parent, OutViewPort)


def main():
    app = QtWidgets.QApplication([])
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt6())
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

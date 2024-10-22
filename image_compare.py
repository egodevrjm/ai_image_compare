import sys
import requests
import random
import datetime
import fal_client
import os
from PyQt6.QtWidgets import (
    QApplication, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QWidget,
    QMessageBox, QComboBox, QScrollArea, QCheckBox, QGridLayout, QGroupBox, QFrame,
    QMainWindow, QStatusBar, QDialog, QStyledItemDelegate
)
from PyQt6.QtGui import QPixmap, QFont, QPalette, QColor, QCursor
from PyQt6.QtCore import Qt, QSize, pyqtSignal  

# Constants
STABILITY_API_URL = "https://api.stability.ai/v2beta/stable-image/generate/sd3"
STABILITY_API_KEY = "API KEY HERE"  # Make sure to set this API key
FAL_API_KEY = os.getenv("FAL_KEY")  # Make sure to set this environment variable
IMAGE_DIR = "generated_images"

if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

def generate_stability_image(prompt, model="sd3.5-large", aspect_ratio="16:9", output_format="png"):
    headers = {
        "authorization": f"Bearer {STABILITY_API_KEY}",
        "accept": "image/*",
    }

    data = {
        "prompt": prompt,
        "model": model,
        "output_format": output_format,
        "aspect_ratio": aspect_ratio,
    }

    files = {
        "none": ('', ''),
    }

    response = requests.post(STABILITY_API_URL, headers=headers, data=data, files=files)

    if response.status_code == 200:
        today = datetime.datetime.today().strftime('%Y-%m-%d')
        random_number = random.randint(1000, 9999)
        file_name = f"{IMAGE_DIR}/generated_image_{today}_{random_number}_{model}.{output_format}"

        with open(file_name, 'wb') as file:
            file.write(response.content)
        
        return file_name
    else:
        return None

def generate_flux_image(prompt, model="fal-ai/flux-pro/v1.1", aspect_ratio="1:1"):
    aspect_ratio_map = {
        "1:1": "square_hd",
        "16:9": "landscape_16_9",
        "4:3": "landscape_4_3",
    }
    flux_size = aspect_ratio_map.get(aspect_ratio, "landscape_4_3")
    model_paths = {
        "flux-1.1-pro": "fal-ai/flux-pro/v1.1",
        "flux-dev": "fal-ai/flux/dev",
        "flux-schnell": "fal-ai/flux/schnell"
    }
    
    model_path = model_paths.get(model, model)

    def on_queue_update(update):
        if isinstance(update, fal_client.InProgress):
            for log in update.logs:
                print(log["message"])

    try:
        result = fal_client.subscribe(
            model_path,
            arguments={
                "prompt": prompt,
                "image_size": flux_size,
                "num_images": 1,
                "enable_safety_checker": True,
                "safety_tolerance": "2"
            },
            with_logs=True,
            on_queue_update=on_queue_update,
        )

        if result and result.get("images"):
            image_url = result["images"][0]["url"]
            response = requests.get(image_url)
            
            if response.status_code == 200:
                today = datetime.datetime.today().strftime('%Y-%m-%d')
                random_number = random.randint(1000, 9999)
                model_name = model.replace("/", "-")  # Clean up model name for filename
                file_name = f"{IMAGE_DIR}/generated_image_{today}_{random_number}_{model_name}.png"
                
                with open(file_name, 'wb') as file:
                    file.write(response.content)
                
                return file_name
    except Exception as e:
        print(f"Error generating Flux image: {e}")
        return None

class ImageViewerDialog(QDialog):
    def __init__(self, image_path, parent=None):
        super().__init__(parent) 
        self.is_dark_mode = self.palette().color(QPalette.ColorRole.Window).lightness() < 128
        self.bg_color = "#1a1a1a" if self.is_dark_mode else "#f5f5f5"
        self.container_bg = "#2d2d2d" if self.is_dark_mode else "white"
        self.border_color = "#404040" if self.is_dark_mode else "#e0e0e0"
        self.text_color = "#ffffff" if self.is_dark_mode else "#333333"
        self.placeholder_color = "#666666" if self.is_dark_mode else "#999999"
        self.accent_color = "#4a90e2"
        self.accent_hover = "#357abd"
        
        self.setWindowTitle("Image Viewer")
        self.setModal(True)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.bg_color};
            }}
            QLabel {{
                color: {self.text_color};
            }}
            QPushButton {{
                background-color: {self.accent_color};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 100px;
            }}
            QPushButton:hover {{
                background-color: {self.accent_hover};
            }}
        """)
        
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        image_container = QFrame()
        image_container.setStyleSheet(f"""
            QFrame {{
                background-color: {self.container_bg};
                border: 1px solid {self.border_color};
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        image_layout = QVBoxLayout(image_container)
        
        image_label = QLabel()
        pixmap = QPixmap(image_path)
        
        scaled_pixmap = pixmap.scaled(
            self.size() - QSize(60, 120), 
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        image_label.setPixmap(scaled_pixmap)
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        image_layout.addWidget(image_label)
        layout.addWidget(image_container)
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignCenter)

class StyledGroupBox(QGroupBox):
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.setStyleSheet("""
            QGroupBox {
                background-color: #ffffff;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 1em;
                padding: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #333333;
            }
        """)

class StyledButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QPushButton:pressed {
                background-color: #2a5f9e;
            }
        """)

class ModelSelector(QFrame):
    selectionChanged = pyqtSignal(str)
    
    def __init__(self, models, parent=None):
        super().__init__(parent)
        self.is_dark_mode = self.palette().color(QPalette.ColorRole.Window).lightness() < 128
        self.bg_color = "#1a1a1a" if self.is_dark_mode else "#f5f5f5"
        self.container_bg = "#2d2d2d" if self.is_dark_mode else "white"
        self.border_color = "#404040" if self.is_dark_mode else "#e0e0e0"
        self.text_color = "#ffffff" if self.is_dark_mode else "#333333"
        self.accent_color = "#4a90e2"
        
        layout = QVBoxLayout(self)
        layout.setSpacing(4)  
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.buttons = []
        
        for category, model_list in models.items():
            header = QLabel(category)
            header.setStyleSheet(f"""
                QLabel {{
                    color: {self.accent_color};  # Using accent color for better visibility
                    font-weight: bold;
                    padding: 12px 8px;  # Increased padding
                    font-size: 13px;
                    margin-top: 8px;  # Added margin
                }}
            """)
            header.setAlignment(Qt.AlignmentFlag.AlignLeft)
            layout.addWidget(header)
            
            for model in model_list:
                btn = QPushButton(model)
                btn.setCheckable(True)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        text-align: left;
                        padding: 10px 16px;  # Increased padding
                        border: none;
                        border-radius: 4px;
                        background-color: {self.container_bg};
                        color: {self.text_color};
                        font-size: 12px;  # Explicit font size
                        margin: 2px 0px;  # Added vertical margin
                    }}
                    QPushButton:hover {{
                        background-color: #3d3d3d;  # Lighter hover color
                        color: white;
                    }}
                    QPushButton:checked {{
                        background-color: {self.accent_color};
                        color: white;
                        font-weight: bold;
                    }}
                """)
                btn.clicked.connect(lambda checked, m=model: self.handle_selection(m))
                layout.addWidget(btn)
                self.buttons.append(btn)
        
        layout.addStretch()  
        
        if self.buttons:
            self.buttons[0].setChecked(True)
            self.current_selection = self.buttons[0].text()

    def handle_selection(self, model):
        for btn in self.buttons:
            if btn.text() != model:
                btn.setChecked(False)
            else:
                btn.setChecked(True)
        
        self.current_selection = model
        self.selectionChanged.emit(model)

    def currentText(self):
        return self.current_selection

    def setEnabled(self, enabled):
        for btn in self.buttons:
            btn.setEnabled(enabled)

class ImageGeneratorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.models = {
            "Stability AI": [
                "sd3.5-large",
                "sd3.5-large-turbo",
                "sd3-large",
                "sd3-large-turbo",
                "sd3-medium"
            ],
            "Flux Models": [
                "flux-1.1-pro",
                "flux-dev",
                "flux-schnell"
            ]
        }
        
        self.is_dark_mode = self.palette().color(QPalette.ColorRole.Window).lightness() < 128
        self.bg_color = "#1a1a1a" if self.is_dark_mode else "#f5f5f5"
        self.container_bg = "#2d2d2d" if self.is_dark_mode else "white"
        self.border_color = "#404040" if self.is_dark_mode else "#e0e0e0"
        self.text_color = "#ffffff" if self.is_dark_mode else "#333333"
        self.placeholder_color = "#666666" if self.is_dark_mode else "#999999"
        self.accent_color = "#4a90e2"  
        self.accent_hover = "#357abd"  
        
        self.initUI()

    def setup_model_combo(self, combo_box):
        combo_box.clear()
        
        header_item = QStyledItemDelegate()
        combo_box.addItem("── Stability AI ──")
        combo_box.setItemData(combo_box.count() - 1, False, Qt.ItemDataRole.UserRole)
        combo_box.setItemData(combo_box.count() - 1, Qt.AlignmentFlag.AlignCenter, Qt.ItemDataRole.TextAlignmentRole)
        
        stability_models = [
            "sd3.5-large",
            "sd3.5-large-turbo",
            "sd3-large",
            "sd3-large-turbo",
            "sd3-medium"
        ]
        for model in stability_models:
            combo_box.addItem(model)
            
        combo_box.addItem("── Flux Models ──")
        combo_box.setItemData(combo_box.count() - 1, False, Qt.ItemDataRole.UserRole)
        combo_box.setItemData(combo_box.count() - 1, Qt.AlignmentFlag.AlignCenter, Qt.ItemDataRole.TextAlignmentRole)
        
        flux_models = [
            "flux-1.1-pro",
            "flux-dev",
            "flux-schnell"
        ]
        for model in flux_models:
            combo_box.addItem(model)

        combo_box.view().installEventFilter(self)
        
        combo_box.setCurrentIndex(1)

    def eventFilter(self, obj, event):
        if isinstance(obj, QComboBox().view().__class__):
            if event.type() == event.Type.MouseButtonPress:
                index = obj.indexAt(event.pos())
                if index.isValid():
                    if not obj.model().data(index, Qt.ItemDataRole.UserRole) is False:
                        return False
                    return True
        return super().eventFilter(obj, event)

    def initUI(self):
        self.setWindowTitle('AI Image Generator Studio')
        self.setMinimumSize(1400, 900)

        base_style = f"""
            QMainWindow {{
                background-color: {self.bg_color};
            }}
            QWidget {{
                color: {self.text_color};
            }}
            QLineEdit {{
                padding: 12px;
                border: 1px solid {self.border_color};
                border-radius: 6px;
                background-color: {self.container_bg};
                color: {self.text_color};
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border-color: {self.accent_color};
                background-color: {self.bg_color};
            }}
            QComboBox {{
                padding: 8px 12px;
                border: 1px solid {self.border_color};
                border-radius: 6px;
                background-color: {self.container_bg};
                color: {self.text_color};
                min-width: 150px;
            }}
            QComboBox:hover {{
                border-color: {self.accent_color};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 8px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.container_bg};
                color: {self.text_color};
                selection-background-color: {self.accent_color};
                border: 1px solid {self.border_color};
                border-radius: 4px;
            }}
            QComboBox::item:!enabled {{
                background-color: {self.container_bg};
                color: {self.placeholder_color};
                font-weight: bold;
                margin-top: 5px;
            }}
            QLabel {{
                color: {self.text_color};
            }}
            QCheckBox {{
                color: {self.text_color};
            }}
            QGroupBox {{
                background-color: {self.container_bg};
                border: 2px solid {self.border_color};
                border-radius: 8px;
                margin-top: 1em;
                padding: 12px;
            }}
            QGroupBox::title {{
                color: {self.text_color};
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                background-color: {self.container_bg};
            }}
            QScrollArea {{
                background-color: {self.bg_color};
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background-color: {self.bg_color};
            }}
            QFrame {{
                background-color: {self.container_bg};
            }}
            QFrame#comparison_frame {{
                background-color: {self.container_bg};
                border: 2px solid {self.border_color};
                border-radius: 8px;
                padding: 10px;
            }}
            QStatusBar {{
                background-color: {self.container_bg};
                color: {self.text_color};
            }}
            QComboBox::item:!enabled {{
                background-color: {self.container_bg};
                color: {self.placeholder_color};
                font-weight: bold;
                margin-top: 5px;
            }}
            QScrollBar:vertical {{
                background-color: {self.container_bg};
                width: 12px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background-color: {self.border_color};
                min-height: 30px;
                border-radius: 6px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {self.accent_color};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """
        
        self.setStyleSheet(base_style)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        header_layout = QHBoxLayout()
        header_label = QLabel("AI Image Generator Studio")
        header_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 10px;
        """)
        header_layout.addWidget(header_label)
        main_layout.addLayout(header_layout)

        prompt_group = StyledGroupBox("Image Prompt")
        prompt_layout = QHBoxLayout()
        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText("Describe the image you want to generate...")
        self.generate_button = StyledButton("Generate Image")
        self.generate_button.clicked.connect(self.on_generate_image)
        prompt_layout.addWidget(self.prompt_input)
        prompt_layout.addWidget(self.generate_button)
        prompt_group.setLayout(prompt_layout)
        main_layout.addWidget(prompt_group)

        content_layout = QHBoxLayout()

        sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setSpacing(15)

        model_group = StyledGroupBox("Primary Model")
        model_layout = QVBoxLayout()
        self.model_selector = ModelSelector(self.models)
        model_layout.addWidget(self.model_selector)
        model_group.setLayout(model_layout)
        sidebar_layout.addWidget(model_group)

        compare_model_group = StyledGroupBox("Comparison Model")
        compare_model_layout = QVBoxLayout()
        self.compare_model_selector = ModelSelector(self.models)
        self.compare_model_selector.setEnabled(False)
        compare_model_layout.addWidget(self.compare_model_selector)
        compare_model_group.setLayout(compare_model_layout)
        sidebar_layout.addWidget(compare_model_group)

        aspect_group = StyledGroupBox("Image Size")
        aspect_layout = QVBoxLayout()
        self.aspect_ratio_combo = QComboBox()
        self.aspect_ratio_combo.addItems(["1:1", "16:9", "4:3"])
        aspect_layout.addWidget(self.aspect_ratio_combo)
        aspect_group.setLayout(aspect_layout)
        sidebar_layout.addWidget(aspect_group)

        self.compare_checkbox = QCheckBox("Enable Model Comparison")
        self.compare_checkbox.stateChanged.connect(self.toggle_compare_models)
        sidebar_layout.addWidget(self.compare_checkbox)

        sidebar_layout.addStretch()
        content_layout.addWidget(sidebar_widget)

        main_content = QWidget()
        main_content_layout = QVBoxLayout(main_content)

        self.comparison_frame = QFrame()
        comparison_layout = QHBoxLayout(self.comparison_frame)
        
        for i, label_text in enumerate(["Primary Model", "Comparison Model"]):
            container = QWidget()
            container_layout = QVBoxLayout(container)
            
            model_label = QLabel(label_text)
            model_label.setStyleSheet(f"""
                font-weight: bold;
                font-size: 14px;
                padding: 5px;
                border-radius: 4px;
                background-color: {self.container_bg};
                color: {self.text_color};
            """)
            model_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            container_layout.addWidget(model_label)
            
            image_label = QLabel("Generated Image will appear here")
            image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            image_label.setMinimumSize(400, 400)
            image_label.setStyleSheet(f"""
                background-color: {self.container_bg};
                border: 2px dashed {self.border_color};
                border-radius: 4px;
                color: {self.placeholder_color};
            """)
            container_layout.addWidget(image_label)
            
            comparison_layout.addWidget(container)
            
            if i == 0:
                self.model_label_1 = model_label
                self.image_label_1 = image_label
            else:
                self.model_label_2 = model_label
                self.image_label_2 = image_label

        self.comparison_frame.hide()
        main_content_layout.addWidget(self.comparison_frame)

        gallery_group = StyledGroupBox("Generated Images Gallery")
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        self.gallery_layout = QGridLayout(scroll_content)
        self.gallery_layout.setSpacing(10)
        scroll_area.setWidget(scroll_content)
        gallery_layout = QVBoxLayout()
        gallery_layout.addWidget(scroll_area)
        gallery_group.setLayout(gallery_layout)
        main_content_layout.addWidget(gallery_group)

        content_layout.addWidget(main_content, stretch=3)
        main_layout.addLayout(content_layout)

        self.statusBar().showMessage('Ready to generate images')

        self.load_gallery()

    def toggle_compare_models(self, state):
        self.comparison_frame.setVisible(state)
        self.compare_model_selector.setEnabled(state)

    def generate_image_with_model(self, prompt, model, aspect_ratio):
        if model in ["flux-1.1-pro", "flux-dev", "flux-schnell"]:
            return generate_flux_image(prompt, model, aspect_ratio)
        else:
            return generate_stability_image(prompt, model, aspect_ratio)
        
    def on_generate_image(self):
        if not self.prompt_input.text():
            QMessageBox.warning(self, "Input Error", "Please enter a valid prompt.")
            return

        if not FAL_API_KEY and any(
            model in ["flux-1.1-pro", "flux-dev", "flux-schnell"] 
            for model in [
                self.model_selector.currentText(),
                self.compare_model_selector.currentText() if self.compare_checkbox.isChecked() else ""
            ]
        ):
            QMessageBox.warning(self, "API Key Error", "Please set your FAL_KEY environment variable to use Flux models.")
            return

        self.statusBar().showMessage('Generating image(s)...')
        self.generate_button.setEnabled(False)

        try:
            self.model_label_1.setText(f"Model: {self.model_selector.currentText()}")
            if self.compare_checkbox.isChecked():
                self.model_label_2.setText(f"Model: {self.compare_model_selector.currentText()}")

            file_name_1 = self.generate_image_with_model(
                self.prompt_input.text(),
                self.model_selector.currentText(),
                self.aspect_ratio_combo.currentText()
            )
            if file_name_1:
                self.display_image(file_name_1, self.image_label_1)
                self.add_to_gallery(file_name_1)

            if self.compare_checkbox.isChecked():
                file_name_2 = self.generate_image_with_model(
                    self.prompt_input.text(),
                    self.compare_model_selector.currentText(),
                    self.aspect_ratio_combo.currentText()
                )
                if file_name_2:
                    self.display_image(file_name_2, self.image_label_2)
                    self.add_to_gallery(file_name_2)

            self.statusBar().showMessage('Image generation completed successfully')
            QMessageBox.information(self, "Success", "Image(s) generated successfully!")

        except Exception as e:
            self.statusBar().showMessage('Error generating image')
            QMessageBox.critical(self, "Error", f"Failed to generate image: {str(e)}")

        finally:
            self.generate_button.setEnabled(True)

    def show_image_viewer(self, image_path):
        dialog = ImageViewerDialog(image_path, self)
        dialog.exec()

    def display_image(self, file_name, label):
        pixmap = QPixmap(file_name)
        scaled_pixmap = pixmap.scaled(
            label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        label.setPixmap(scaled_pixmap)
        label.setStyleSheet(f"""
            QLabel {{
                background-color: {self.container_bg};
                border: 2px solid {self.border_color};
                border-radius: 4px;
            }}
        """)

    def add_to_gallery(self, file_path, row=0, col=0):
        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {self.container_bg};
                border: 1px solid {self.border_color};
                border-radius: 8px;
                padding: 10px;
            }}
            QFrame:hover {{
                border-color: {self.accent_color};
                background-color: {self.bg_color};
            }}
        """)
        container.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        layout = QVBoxLayout(container)
        layout.setSpacing(8)  
        
        image_container = QFrame()
        image_container.setStyleSheet(f"""
            QFrame {{
                background-color: {self.container_bg};
                border-radius: 6px;
                padding: 8px;
            }}
        """)
        image_layout = QVBoxLayout(image_container)
        image_layout.setContentsMargins(0, 0, 0, 0)
        
        image_label = QLabel()
        pixmap = QPixmap(file_path)
        scaled_pixmap = pixmap.scaled(
            200, 200,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        image_label.setPixmap(scaled_pixmap)
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_layout.addWidget(image_label)
        
        layout.addWidget(image_container)
        
        model_name = os.path.basename(file_path).split('_')[-1].split('.')[0]
        model_label = QLabel(model_name)
        model_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        model_label.setStyleSheet(f"""
            color: {self.text_color};
            font-size: 12px;
            padding: 4px 8px;
            background-color: {self.bg_color};
            border-radius: 4px;
        """)
        layout.addWidget(model_label)
        
        container.mousePressEvent = lambda e: self.show_image_viewer(file_path)
        self.gallery_layout.addWidget(container, row, col)

    def load_gallery(self):
        row = col = 0
        if os.path.exists(IMAGE_DIR):
            for file_name in sorted(os.listdir(IMAGE_DIR), reverse=True):
                if file_name.endswith((".png", ".jpg", ".jpeg")):
                    self.add_to_gallery(os.path.join(IMAGE_DIR, file_name), row, col)
                    col += 1
                    if col > 3:  
                        col = 0
                        row += 1

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = ImageGeneratorApp()
    window.show()
    sys.exit(app.exec())

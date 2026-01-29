# hmi.py
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView 
from kivy.graphics.texture import Texture
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.modalview import ModalView
from kivy.app import App
import cv2
import json
import os

# Try to import logger, otherwise use standard print
try:
    from config import COLOR_SCHEME, logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("HMI")

SETTINGS_FILE = "user_settings.json"

# =========================================================
# 1. REMOVED KEYPAD POPUP CLASS
# =========================================================
# (KeypadPopup class removed)

# =========================================================
class LocationConfirmPopup(ModalView):
    def __init__(self, location_data, confirm_callback, cancel_callback, **kwargs):
        super().__init__(**kwargs)
        self.confirm_callback = confirm_callback
        self.cancel_callback = cancel_callback
        self.size_hint = (None, None)
        self.size = (500, 350)
        self.auto_dismiss = False 
        self.background_color = (0, 0, 0, 0.9)

        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        # Header
        layout.add_widget(Label(
            text="LOCATION UPDATE", font_size='24sp', color=(1, 0.8, 0, 1), 
            bold=True, size_hint_y=None, height=50
        ))

        # Location Info
        loc_text = location_data.get('location', 'New Assignment')
        msg = f"New Location:\n[size=36][b]{loc_text}[/b][/size]\n\nPlease Confirm."
        
        layout.add_widget(Label(
            text=msg, font_size='20sp', halign='center', markup=True
        ))

        # === BUTTONS CONTAINER ===
        btn_layout = BoxLayout(orientation='horizontal', spacing=20, size_hint_y=None, height=70)

        # Cancel Button (Red)
        btn_cancel = Button(
            text="CANCEL", 
            background_color=(0.9, 0.2, 0.2, 1), bold=True, font_size='22sp'
        )
        btn_cancel.bind(on_release=self._cancel)
        btn_layout.add_widget(btn_cancel)

        # Confirm Button (Green)
        btn_confirm = Button(
            text="CONFIRM", 
            background_color=(0, 0.8, 0, 1), bold=True, font_size='22sp'
        )
        btn_confirm.bind(on_release=self._confirm)
        btn_layout.add_widget(btn_confirm)

        layout.add_widget(btn_layout)
        self.add_widget(layout)

    def _confirm(self, instance):
        if self.confirm_callback:
            self.confirm_callback()
        self.dismiss()

    def _cancel(self, instance):
        if self.cancel_callback:
            self.cancel_callback()
        self.dismiss()

# =========================================================
# 3. MAIN HMI CLASS (COMPACT & RESPONSIVE)
# =========================================================
class ProfessionalTopCameraHMI(BoxLayout):
    def __init__(self, top_camera, controller, **kwargs):
        super().__init__(**kwargs)
        self.top_camera = top_camera
        self.controller = controller
        self.orientation = 'horizontal'
        
        self.customer_map = {} 
        # self.current_target = 0 
        self.last_count_seen = -1 
        self.ignore_camera_updates = False
        self.confirmed_location = None 
        self.current_popup = None
        
        print("[INIT] HMI Initializing...")
        self._build_ui()
        # self._load_last_target() # Removed
        
        Clock.schedule_once(lambda dt: self._trigger_refresh_logic(), 1)
        Clock.schedule_interval(self._update_camera_feed, 1.0 / 30.0)

    # def _load_last_target(self): ... REMOVED
    # def _save_target_to_disk(self): ... REMOVED

    def _build_ui(self):
        # --- COMPACT UI CONFIGURATION (1024x600) ---
        Window.size = (1024, 600) 
        Window.clearcolor = (0.96, 0.97, 0.98, 1)

        self.spacing = 5
        self.padding = 5
        
        # === LEFT PANEL (Camera - Takes 65% of width) ===
        left_panel = BoxLayout(orientation='vertical', size_hint_x=0.65)
        self.camera_image = Image(allow_stretch=True, keep_ratio=True)
        left_panel.add_widget(self.camera_image)
        self.add_widget(left_panel)
        
        # === RIGHT PANEL (Controls - Takes 35% of width) ===
        right_panel = BoxLayout(orientation='vertical', size_hint_x=0.35, padding=5, spacing=5)
        
        # 1. Title & Exit Button
        header = BoxLayout(size_hint_y=0.1) 
        header.add_widget(Label(text='[b]PALLETIZER[/b]', markup=True, color=(0.2, 0.4, 0.7, 1), font_size='18sp', halign='left', valign='middle'))
        
        exit_btn = Button(text='X', background_color=(0.9, 0.1, 0.1, 1), size_hint_x=None, width=40, font_size='16sp', bold=True)
        exit_btn.bind(on_release=lambda x: App.get_running_app().stop())
        header.add_widget(exit_btn)
        right_panel.add_widget(header)

        # 2. Live Count Display (Replacing Target Counter)
        self.count_display_label = Label(
            text="0", 
            font_size='60sp', 
            bold=True,
            color=(0.2, 0.4, 0.7, 1),
            size_hint_y=0.25
        )
        right_panel.add_widget(self.count_display_label)
        
        self.status_label = Label(text='Live Count', color=(1, 0.5, 0, 1), font_size='16sp', bold=True, size_hint_y=0.05)
        right_panel.add_widget(self.status_label)

        # 3. Customer Selection (Grouped in one row)
        cust_row = BoxLayout(size_hint_y=0.1, spacing=2)
        
        self.customer_spinner = Spinner(
            text='Select Customer', 
            values=[], 
            background_color=(0.2, 0.6, 0.8, 1),
            size_hint_x=0.7
        )
        self.customer_spinner.bind(text=self._on_settings_change)
        
        self.refresh_btn = Button(text='R', size_hint_x=0.3, background_color=(0.5, 0.5, 0.5, 1))
        self.refresh_btn.bind(on_release=self._on_refresh_click)
        
        cust_row.add_widget(self.customer_spinner)
        cust_row.add_widget(self.refresh_btn)
        right_panel.add_widget(cust_row)

        # 4. Scanned List (Compact ScrollView)
        list_container = BoxLayout(orientation='vertical', size_hint_y=0.35) 
        list_container.add_widget(Label(text='Scanned IDs:', size_hint_y=None, height=20, color=(0.5, 0.5, 0.5, 1)))
        
        self.id_scroll = ScrollView()
        self.id_label = Label(
            text='Waiting...', 
            font_size='13sp', 
            color=(0.2, 0.2, 0.2, 1),
            size_hint_y=None, 
            halign='center', 
            valign='top'
        )
        self.id_label.bind(texture_size=self.id_label.setter('size'))
        self.id_label.bind(width=lambda *x: self.id_label.setter('text_size')(self.id_label, (self.id_label.width, None)))
        
        self.id_scroll.add_widget(self.id_label)
        list_container.add_widget(self.id_scroll)
        right_panel.add_widget(list_container)

        # 5. Control Buttons (Grid Layout)
        btn_grid = GridLayout(cols=1, spacing=5, size_hint_y=0.2)
        
        self.reset_btn = Button(text='RESET', background_color=(1, 0.65, 0.3, 1), font_size='14sp', bold=True)
        self.reset_btn.bind(on_release=self._do_reset)
        btn_grid.add_widget(self.reset_btn)



        # self.save_btn = Button(text='SAVE', background_color=(0.2, 0.6, 0.8, 1), disabled=True, font_size='14sp', bold=True)
        # self.save_btn.bind(on_press=self._do_save_local)
        # btn_grid.add_widget(self.save_btn)

        right_panel.add_widget(btn_grid)

        # Submit Button (Bottom)
        self.submit_btn = Button(
            text='SUBMIT TO CLOUD', 
            background_color=(0.75, 0.75, 0.75, 1), 
            disabled=True, 
            font_size='16sp', 
            bold=True,
            size_hint_y=0.1
        )
        self.submit_btn.bind(on_press=self._do_submit)
        right_panel.add_widget(self.submit_btn)

        # Footer
        self.notification_label = Label(text='Ready', color=(0.4, 0.7, 0.4, 1), font_size='12sp', size_hint_y=0.05)
        right_panel.add_widget(self.notification_label)
        
        self.add_widget(right_panel)

    # === LOGIC HANDLERS (Same as before) ===
    def on_websocket_message(self, data):
        new_location = data.get('location', 'Unknown')
        if self.confirmed_location == new_location:
            return
        Clock.schedule_once(lambda dt: self._show_location_popup(data), 0)

    def _show_location_popup(self, data):
        if self.current_popup:
            self.current_popup.dismiss()
        self.current_popup = LocationConfirmPopup(
            location_data=data,
            confirm_callback=lambda: self._on_location_confirmed(data),
            cancel_callback=lambda: self._on_location_cancelled(data)
        )
        self.current_popup.open()

    def _on_location_confirmed(self, data):
        loc_text = data.get('location', 'Unknown')
        self.confirmed_location = loc_text
        self._update_notification(f"Loc: {loc_text}", (0, 1, 0, 1))
        self._update_submit_button(len(self.controller.scanned_kegs))

        # Auto-submit if ready (User requested auto-click behavior)
        if not self.submit_btn.disabled:
            self._update_notification("Auto-Sending...", (0.2, 0.6, 1.0, 1))
            # Use trigger_action to visually and functionally simulate the click
            Clock.schedule_once(lambda dt: self.submit_btn.trigger_action(0.2), 0.5)

    def _on_location_cancelled(self, data):
        self._update_notification("Loc Cancelled", (1, 0.5, 0, 1))


    def _on_settings_change(self, instance, text):
        if text in self.customer_map:
            c_id = self.customer_map[text]
            self.controller.set_customer(c_id)
            self._update_notification(f"Customer: {text}", (0.2, 0.8, 0.2, 1))
            self._update_submit_button(len(self.controller.scanned_kegs))

    def _on_refresh_click(self, instance):
        self._update_notification("Refreshing...", (0.2, 0.6, 1.0, 1))
        Clock.schedule_once(lambda dt: self._trigger_refresh_logic(), 0.1)

    def _trigger_refresh_logic(self):
        customers = self.controller.get_customers()
        if customers:
            self.customer_map = {c['name']: c['id'] for c in customers}
            self.customer_spinner.values = list(self.customer_map.keys())
            if self.customer_spinner.text not in self.customer_map:
                self.customer_spinner.text = 'Select Customer'
            self._update_notification("Data Updated", (0.3, 0.75, 0.5, 1))
        else:
            self._update_notification("API Error", (0.9, 0.3, 0.3, 1))

        c_name = self.customer_spinner.text
        if c_name in self.customer_map:
            c_id = self.customer_map[c_name]
            self.controller.set_customer(c_id)
            current = len(self.controller.scanned_kegs)
            
            # Removed target comparison logic
            self.status_label.text = "Live Count"
            self.status_label.color = (1, 0.65, 0, 1)

            self._update_submit_button(current)

    # def _do_save_local(self, instance):
    #     saved_count = self.controller.save_locally()
    #     self._update_notification(f"Saved: {saved_count}", (0.3, 0.75, 0.5, 1))

    def _do_reset(self, instance):
        try:
            print("Reset button pressed")
            self.controller.reset_session()
            # self.controller.target_count = 0
            self.confirmed_location = None
            # self.current_target = 0
            self.count_display_label.text = "0"
            # self._save_target_to_disk()
            
            self.status_label.text = "Live Count"
            self.id_label.text = "Waiting..."
            self._update_submit_button(0)
            # self.save_btn.disabled = True
            # self.save_btn.background_color = (0.75, 0.75, 0.75, 1)
            self._update_notification("Reset Done", (0.4, 0.65, 0.95, 1))
            
            self.ignore_camera_updates = True
            Clock.schedule_once(self._resume_camera, 2.0)
        except Exception as e:
            logger.error(f"Reset Error: {e}")
            self._update_notification("Reset Failed", (0.9, 0.1, 0.1, 1))

    def _resume_camera(self, dt):
        self.ignore_camera_updates = False

    def _do_submit(self, instance):
        self.submit_btn.disabled = True
        self.submit_btn.text = "SENDING..."
        Clock.schedule_once(lambda dt: self._process_submission(), 0.1)

    def _process_submission(self):
        current_area = self.confirmed_location if self.confirmed_location else "Unknown"
        result = self.controller.submit_batch(area_name=current_area)
        
        if result['success']:
            self.controller.reset_session()
            c_id = self.customer_map.get(self.customer_spinner.text)
            if c_id: self.controller.set_target_and_customer(c_id)
            
            self.id_label.text = "Waiting..."
            self.submit_btn.text = "SUBMIT TO CLOUD"
            # self.save_btn.disabled = True
            
            self.status_label.text = "Live Count"
            self.count_display_label.text = "0"
            self.status_label.color = (1, 0.65, 0, 1)
            
            self._update_submit_button(0)
            self._update_notification("Success!", (0.3, 0.75, 0.5, 1))
        else:
            self._update_notification("Failed", (0.95, 0.4, 0.35, 1))
            self.submit_btn.disabled = False 
            self.submit_btn.text = "SUBMIT TO CLOUD"

    def _update_camera_feed(self, dt):
        if self.top_camera.is_active:
            ret, frame = self.top_camera.get_overhead_view()
            if ret and frame is not None:
                processed, count, reached = self.controller.process_frame(frame)
                
                if not self.ignore_camera_updates:
                    # Update count display directly
                    self.count_display_label.text = str(count)
                    self.status_label.text = "Live Count"
                    self.status_label.color = (1, 0.65, 0, 1)
                    
                    scanned_list = self.controller.get_scanned_list()
                    self.id_label.text = "\n".join(scanned_list) if scanned_list else "Waiting..."
                    
                    self._update_submit_button(count)
                    
                    # if count > 0:
                    #     self.save_btn.disabled = False
                    #     self.save_btn.background_color = (0.2, 0.6, 1.0, 1)
                    # else:
                    #     self.save_btn.disabled = True
                    #     self.save_btn.background_color = (0.75, 0.75, 0.75, 1)

                buf = cv2.flip(processed, 0).tobytes()
                texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
                texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
                self.camera_image.texture = texture

    def _update_submit_button(self, count):
        customer_selected = self.customer_spinner.text in self.customer_map
        location_confirmed = self.confirmed_location is not None
        # count_reached = (count == target and target > 0)
        has_items = count > 0

        if has_items and customer_selected and location_confirmed:
            self.submit_btn.disabled = False
            self.submit_btn.background_color = (0.3, 0.75, 0.5, 1)
        else:
            self.submit_btn.disabled = True
            self.submit_btn.background_color = (0.75, 0.75, 0.75, 1)

    def _update_notification(self, text, color):
        self.notification_label.text = text
        self.notification_label.color = color
import pygame as pg

class Textfield:
    
    def __init__(self, 
                 x, 
                 y, 
                 width, 
                 height, 
                 default_text, 
                 color_normal=None, 
                 color_clicked=None, 
                 disabled=False, 
                 semi_disabled=False, 
                 click_color_enabled=False, 
                 obj_id = None,
                 on_mouse_leave_action = None):
        
        self.rect = pg.Rect(x, y, width, height)
        self.text = ""
        self.default_text = default_text
        self.font = pg.font.Font(None, 36)
        self.on_mouse_leave_action = on_mouse_leave_action
        
        # id for each object
        self.obj_id = obj_id
        
        # Default colors
        self.default_color_normal = (100, 100, 200)
        self.default_color_clicked = (50, 50, 150)
        self.disabled_color = (150, 150, 150)  # Gray color when disabled
        self.semi_disabled_color = (120, 120, 180)  # Slightly faded color for semi-disabled
        
        self.color_normal = color_normal if color_normal else self.default_color_normal
        self.color_clicked = color_clicked if color_clicked else self.default_color_clicked
        
        self.disabled = disabled  # Fully disabled state
        self.semi_disabled = semi_disabled  # Semi-disabled state
        self.click_color_enabled = click_color_enabled  # Enables or disables click color change
        
        self.color = self.get_current_color()

        self.active = False
        self.mouse_was_inside = False  # Track if mouse was previously inside the field
        self.on_mouse_leave = on_mouse_leave_action  # Callback function for mouse leave event
        
    
    def get_current_color(self):
        if self.disabled:
            return self.disabled_color
        elif self.semi_disabled:
            return self.semi_disabled_color
        return self.color_normal

    def set_disabled(self, disabled):
        """Enable or disable the button."""
        self.disabled = disabled
        self.color = self.get_current_color()
        self.update_hover_color()
    
    def set_semi_disabled(self, semi_disabled):
        """Enable or semi-disable the button. If clicked while semi-disabled, it becomes fully enabled."""
        self.semi_disabled = semi_disabled
        self.color = self.get_current_color()
        self.update_hover_color()

    def draw(self, surface):
        pg.draw.rect(surface, self.color, self.rect)
        text_surface = self.font.render(self.text, True, (255, 255, 255))
        surface.blit(text_surface, (self.rect.x + (self.rect.width - text_surface.get_width()) // 2,
                                    self.rect.y + (self.rect.height - text_surface.get_height()) // 2))

    def handle_event(self, event):
        if self.disabled:
            return None  # Ignore events when fully disabled
        
        if event.type == pg.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                print(f"CLICKED on {self.text} at {event.pos}")
                self.active = True
                if self.text == self.default_text:  # If text is empty, clear the default text when clicked
                    self.text = ""
                print("Active")
            else:
                self.active = False
                self.color = self.color_normal
                print("Not active")
            
            if self.semi_disabled:
                self.set_semi_disabled(False)  # Clicking when semi-disabled enables the button
        
        if self.active:
            if event.type == pg.KEYDOWN: 

                if event.key == pg.K_ESCAPE or event.key == pg.K_RETURN:
                    self.handle_mouse_leave()
                
                # Check for backspace 
                if event.key == pg.K_BACKSPACE: 

                    # get text input from 0 to -1 i.e. end. 
                    self.text = self.text[:-1] 

                # Unicode standard is used for string 
                # formation 
                else: 
                    self.text += event.unicode

            if self.active: 
                self.color = self.color_clicked 
            else: 
                self.color = self.color_normal 
                
             # Handle mouse movement events for leave detection
            if event.type == pg.MOUSEMOTION:
                mouse_is_inside = self.rect.collidepoint(event.pos)
                
                # If mouse was inside but is now outside, trigger leave action
                if self.mouse_was_inside and not mouse_is_inside:
                    self.handle_mouse_leave()
                
                # Update the tracking variable
                self.mouse_was_inside = mouse_is_inside

            
            
        if not self.active and not self.text:
            # If the textbox is not active and there is no text, show default text
            self.text = self.default_text
        
       
        return None
    
    def handle_mouse_leave(self):
        """Called when the mouse leaves the textfield"""
        print(f"Mouse left textfield {self.obj_id}")
        if self.on_mouse_leave_action:
            self.on_mouse_leave_action() 
    
    def get_string(self):
        return self.text
    
    def is_field_empty(self):
        return True if self.text == self.default_text or self.text == "" else False

    def get_id(self):
        return self.obj_id
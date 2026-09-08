"""Find helpers — thin re-export layer (ui_automation canonical)."""
from tools.ui_automation import do_find_element, do_find_elements, do_smart_find

__all__ = ["do_find_element", "do_find_elements", "do_smart_find"]

"""
KLIPS2 Tools Package
"""
from .register import create_klips2_register_tool
from .apply import create_klips2_apply_tool
from .password import create_klips2_change_password_tool
from .courses import create_klips2_get_course_details_tool
from .activate import create_klips2_activate_account_tool
from .address import create_klips2_change_address_tool

__all__ = [
    "create_klips2_register_tool",
    "create_klips2_apply_tool",
    "create_klips2_change_password_tool",
    "create_klips2_get_course_details_tool",
    "create_klips2_activate_account_tool",
    "create_klips2_change_address_tool"
]

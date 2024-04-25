import dataclasses
from typing import Self


@dataclasses.dataclass(kw_only=True)
class _NavLink:
    url: str
    label: str
    is_active: bool = False


@dataclasses.dataclass(kw_only=True)
class SubmenuItem(_NavLink):
    """A sub-menu in the navbar

    See base.html for rendering.
    """

    is_divider: bool = False

    @classmethod
    def build_divider(cls) -> Self:
        return cls(url='', label='', is_divider=True)


@dataclasses.dataclass(kw_only=True)
class NavbarItem(_NavLink):
    """A navbar item

    See context_processors.navbar_menu() for definition of the menu.
    See base.html for rendering.
    """

    # Note: when submenu exists url is ignored but not label!
    submenu: list[SubmenuItem] = dataclasses.field(default_factory=list)

    @classmethod
    def build_submenu(cls, *, label: str, submenu: list[SubmenuItem]) -> Self:
        return cls(url='', label=label, submenu=submenu)

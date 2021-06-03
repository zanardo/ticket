from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    username: str
    is_admin: bool
    name: Optional[str]
    email: Optional[str]

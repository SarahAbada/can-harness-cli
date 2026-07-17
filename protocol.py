from dataclasses import dataclass
from typing import Optional, List
# imports

DELIMITER = ":"
TERMINATOR = "\n" 
VALID_BUSES = {"fdcan", "can", "udp", "tcan", "afea", "afeb"} # set of all valid transport mediums
VALID = MODULES = {"head", "hub1", "hub2", "hub3"} # set of all valid targets for routing
# defining constants at the top so they're easy to change if needed / as the project evolves

@dataclass
class HarnessCommand:
    action: str
    target: Optional[str] = None # can hold a str or be None
    parameter: Optional[str] = None # can hold a str or be None
    # no init function, dataclass manages that by itself
    def __post_init__(self):
        """
        Runs automatically after __init__ to validate fields.
        """
        # ensure target is valid if it is provided
        if self.target is not None:
            valid_targets = VALID_BUSES.union(VALID = MODULES) # combine both sets into one master set of destinations
            if self.target not in valid_targets:
                raise ValueError(f"Invalid target '{self.target}'. Must be one of {valid_targets}")
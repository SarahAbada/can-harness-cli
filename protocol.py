from dataclasses import dataclass
from typing import Optional, List
# imports

DELIMITER = ":"
TERMINATOR = "\n" 
VALID_BUSES = {"fdcan", "can", "udp", "tcan", "afea", "afeb"} # set of all valid transport mediums
VALID_MODULES = {"head", "hub1", "hub2", "hub3"} # set of all valid targets for routing
# defining constants at the top so they're easy to change if needed / as the project evolves

# Head Module Rule Configuration
HEAD_RULES = {
    "ping": {"targets": {None}, "parameters": {None}},
    "send": {"targets": {"can", "fdcan", "udp"}, "parameters": "hex"},
    "sniff": {"targets": {"can", "fdcan", "udp"}, "parameters": {"on", "off"}},
    "bus": {"targets": {"status", "errors"}, "parameters": {None}},
    "status": {"targets": VALID_MODULES, "parameters": {None}},
    "reset": {"targets": VALID_MODULES, "parameters": {None}},
}

# Hub Module Rule Configuration
HUB_RULES = {
    "ping": {"targets": {None}, "parameters": {None}},
    "send": {"targets": {"fdcan", "tcan", "afea", "afeb"}, "parameters": "hex"},
    "sniff": {"targets": {None}, "parameters": {"on", "off"}},  # sniff:<on/off> has no bus target
    "reset": {"targets": {None}, "parameters": {None}},
}

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
            valid_targets = VALID_BUSES.union(VALID_MODULES) # combine both sets into one master set of destinations
            if self.target not in valid_targets:
                raise ValueError(f"Invalid target '{self.target}'. Must be one of {valid_targets}")
    def validate(self, destination: str) -> bool:
        """
        Validates the command against the protocol rules for either 'head' or 'hub'.
        Raises ValueError if the command violates the protocol constraints.
        """
        dest = destination.lower()
        if dest == "head":
            ruleset = HEAD_RULES
        elif dest == "hub":
            ruleset = HUB_RULES
        else:
            raise ValueError(f"Unknown destination type '{destination}'. Must be 'head' or 'hub'.")

        # 1. Verify the action exists for this device type
        if self.action not in ruleset:
            raise ValueError(f"Action '{self.action}' is invalid for a {dest} module.")

        rule = ruleset[self.action]

        # 2. Validate the target field
        if self.target not in rule["targets"]:
            raise ValueError(
                f"Invalid target '{self.target}' for command '{self.action}' on {dest}. "
                f"Expected one of: {rule['targets']}"
            )

        # 3. Validate the parameter field
        expected_params = rule["parameters"]

        if expected_params == "hex":
            # Ensure parameter is not None and is a valid hexadecimal string
            if self.parameter is None:
                raise ValueError(f"Command '{self.action}' requires a hex data parameter.")
            # Simple check if string is valid hex characters
            try:
                int(self.parameter, 16)
            except (ValueError, TypeError):
                raise ValueError(f"Parameter '{self.parameter}' must be a valid hex string.")
                
        elif self.parameter not in expected_params:
            raise ValueError(
                f"Invalid parameter '{self.parameter}' for command '{self.action}' on {dest}. "
                f"Expected one of: {expected_params}"
            )

        return True
    def to_string(self) -> str:
        """
        Serializes the validated command fields into the protocol's 
        colon-delimited string format, ending with a newline.
        """
        # Collect only fields that aren't None
        components = [self.action]
        if self.target is not None:
            components.append(str(self.target))
        if self.parameter is not None:
            components.append(str(self.parameter))
            
        # Join components with ':' and append '\n'
        return DELIMITER.join(components) + TERMINATOR

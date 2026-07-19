from protocol import HarnessCommand

def test_command(name: str, cmd: HarnessCommand, dest: str):
    """Utility to test a command configuration and print results."""
    print(f"--- Testing: {name} ---")
    try:
        # 1. Run our lookup-table validation rules
        cmd.validate(destination=dest)
        print(f"Result:   VALID")
        
        # 2. Compile to raw protocol string
        raw_string = cmd.to_string()
        # Use repr() so we can visually confirm the hidden '\n' character
        print(f"Encoded:  {repr(raw_string)}") 
        
    except ValueError as e:
        print(f"Result:   INVALID")
        print(f"Reason:   {e}")
    print()

def run_tests():
    # ==== HEAD MODULE TESTS ====
    print("=========================")
    print("   HEAD MODULE SAMPLES   ")
    print("=========================\n")
    
    # Valid Head Ping
    test_command("Valid Head Ping", 
                 HarnessCommand(action="ping"), 
                 dest="head")
                 
    # Valid Head Data Send
    test_command("Valid Head CAN Send", 
                 HarnessCommand(action="send", target="can", parameter="12A3F"), 
                 dest="head")
                 
    # Invalid Head CAN Send (bad hex characters)
    test_command("Invalid Head CAN Send (Bad Hex)", 
                 HarnessCommand(action="send", target="can", parameter="12GHI"), 
                 dest="head")
                 
    # Invalid Head Target for Sniff
    test_command("Invalid Head Sniff Target", 
                 HarnessCommand(action="sniff", target="tcan", parameter="on"), 
                 dest="head")


    # ==== HUB MODULE TESTS ====
    print("=========================")
    print("   HUB MODULE SAMPLES    ")
    print("=========================\n")
    
    # Valid Hub Reset (Notice target and parameter are None)
    test_command("Valid Hub Reset", 
                 HarnessCommand(action="reset"), 
                 dest="hub")
                 
    # Valid Hub TCAN Send
    test_command("Valid Hub TCAN Send", 
                 HarnessCommand(action="send", target="tcan", parameter="AABBCC"), 
                 dest="hub")
                 
    # Invalid Hub Sniff (Hub sniff shouldn't have a bus target name)
    test_command("Invalid Hub Sniff (Tried passing a bus)", 
                 HarnessCommand(action="sniff", target="fdcan", parameter="on"), 
                 dest="hub")

if __name__ == "__main__":
    run_tests()
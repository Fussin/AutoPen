class ToolExecutionError(Exception):
    """Custom exception for tool execution failures."""
    pass

class ToolNotFoundError(Exception):
    """Custom exception for when a required tool is not found."""
    def __init__(self, tool_name, install_cmd=None):
        self.tool_name = tool_name
        self.install_cmd = install_cmd
        message = f"Tool '{tool_name}' not found. Please install it."
        if install_cmd:
            message += f"\nInstallation command: {install_cmd}"
        super().__init__(message)

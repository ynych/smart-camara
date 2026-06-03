class BaseAgent:
    """Agent基类"""
    name = "base"
    description = "Agent基类"

    def __init__(self):
        self.tools = {}

    def register_tool(self, name, tool):
        """注册工具"""
        self.tools[name] = tool

    def execute(self, **kwargs):
        """执行Agent任务（子类实现）"""
        raise NotImplementedError

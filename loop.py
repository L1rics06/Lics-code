"""Agent 主循环模块：加载工具定义与配置，驱动模型-工具交互循环直至生成最终回答"""

from openai import OpenAI
import yaml
import json
from client import display_tool_call
from rich.console import Console
from utils import *

# 工具名称 -> 处理函数的映射表
TOOL_HANDLERS = {
    "run_bash": lambda **kw: run_bash(kw.get("command", "")),
    "read_file": lambda **kw: read_file(kw.get("file_path", "")),
    "write_file": lambda **kw: write_file(kw.get("file_path", ""), kw.get("content", "")),
    "append_file": lambda **kw: append_file(kw.get("file_path", ""), kw.get("content", "")),
}

# 加载配置文件，初始化模型客户端
with open("./config.yaml", "r") as f:
    config = yaml.safe_load(f)
    llm_client = OpenAI(
        api_key=config["model"]["api_key"],
        base_url=config["model"]["base_url"]
    )
    model = config["model"]["model_name"]

# 加载工具定义列表
with open("./tools.json", "r") as f:
    tools_list = json.load(f)

console = Console()


def agent_loop(query, tools):
    """Agent 主循环：持续调用模型并执行工具，直到模型返回最终回答"""
    messages = [{"role": "user", "content": query}]

    while True:
        with console.status("[bold green]正在思考或生成回答...[/bold green]", spinner="dots"):
            response = llm_client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools
            )

        message = response.choices[0].message
        messages.append(message)

        if response.choices[0].finish_reason != "tool_calls":
            return response.choices[0].message.content + " (Finish Reason: " + response.choices[0].finish_reason + ")"

        display_tool_call(response.choices[0].message.tool_calls[0], console)

        for block in response.choices[0].message.tool_calls:
            tool_name = block.function.name
            try:
                arguments = json.loads(block.function.arguments)
            except json.JSONDecodeError:
                arguments = {}

            handler = TOOL_HANDLERS.get(tool_name)
            if handler:
                try:
                    output = handler(**arguments)
                except Exception as e:
                    output = f"工具执行失败: {str(e)}"
            else:
                output = f"未知工具: {tool_name}"

            messages.append({
                "role": "tool",
                "tool_call_id": block.id,
                "name": tool_name,
                "content": output
            })


if __name__ == "__main__":
    input_query = sanitize_text(input("Enter your query: ").strip())
    result = agent_loop(input_query, tools_list)
    print("Final Result:", result)

from openai import OpenAI
import json,yaml
import tools
from utils import *
from pathlib import Path
from client import get_display

# 全局单例 Todomanager
_todo_manager = Todomanager()

#工具映射
SUB_TOOL_HANDLERS = {
    "run_bash": lambda **kw: run_bash(kw.get("command", "")),
    "read_file": lambda **kw: read_file(kw.get("file_path", "")),
    "write_file": lambda **kw: write_file(kw.get("file_path", ""), kw.get("content", "")),
    "append_file": lambda **kw: append_file(kw.get("file_path", ""), kw.get("content", "")),
    "todo": lambda **kw: _todo_manager.update_tasks(kw.get("tasks", []))
}

tools_list = tools.CHILD_TOOLS


with open("./config.yaml", "r") as f:
    config = yaml.safe_load(f)
    llm_client = OpenAI(
        api_key=config["model"]["api_key"],
        base_url=config["model"]["base_url"]
    )
    model = config["model"]["model_name"]


def run_subagent(prompt:str)-> str:
    "运行子Agent，执行工具并返回结果"
    display = get_display()
    sub_messages = [{"role": "user", "content": prompt}]
    used_todo = False
    rounds_since_todo = 0
 
    for _ in range(30):
        response = llm_client.chat.completions.create(
            model=model,
            messages=sub_messages,
            tools=tools_list
        )

        message = response.choices[0].message
        sub_messages.append(message.model_dump(exclude_none=True))

        finish_reason = response.choices[0].finish_reason
        if finish_reason != "tool_calls":
            return message.content

        tool_calls = message.tool_calls or []

        # 遍历处理所有并发调用的工具
        for block in tool_calls:
            tool_name = block.function.name
            try:
                arguments = json.loads(block.function.arguments)
            except json.JSONDecodeError:
                arguments = {}

            handler = SUB_TOOL_HANDLERS.get(tool_name)
            if handler:
                try:
                    output = handler(**arguments)

                    #强制确保 tool 的返回值绝对是字符串
                    if output is None:
                        output = "Success"
                    elif not isinstance(output, str):
                        output = str(output)

                except Exception as e:
                    output = f"工具执行失败: {str(e)}"
            else:
                output = f"未知工具: {tool_name}"
                display.display_warning(f"子Agent 未知工具调用: {tool_name}")

            if tool_name == "todo":
                used_todo = True

            rounds_since_todo = 0 if used_todo else rounds_since_todo + 1

            sub_messages.append({
                "role": "tool",
                "tool_call_id": block.id,
                "name": tool_name,
                "content": output
            })

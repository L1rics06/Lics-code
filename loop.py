"""Agent 主循环模块：加载工具定义与配置，驱动模型-工具交互循环直至生成最终回答"""

from openai import OpenAI
import yaml
import json
from utils import *
from client import get_display, console

# 工具名称 -> 处理函数的映射表
TOOL_HANDLERS = {
    "run_bash": lambda **kw: run_bash(kw.get("command", "")),
    "read_file": lambda **kw: read_file(kw.get("file_path", "")),
    "write_file": lambda **kw: write_file(kw.get("file_path", ""), kw.get("content", "")),
    "append_file": lambda **kw: append_file(kw.get("file_path", ""), kw.get("content", "")),
    "todo": lambda **kw: Todomanager().update_tasks(kw.get("tasks", []))
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


def agent_loop(query, tools):
    """Agent 主循环：持续调用模型并执行工具，直到模型返回最终回答"""
    # 初始化终端显示器
    display = get_display()
    display.start()
    
    messages = [{"role": "user", "content": query}]
    rounds_since_todo = 0
    used_todo = False
    
    # 显示开始消息
    display.display_info(f"开始处理查询: {query[:50]}...")
    display.show_task_summary()
    
    round_count = 0
    
    while True:
        round_count += 1
        display.display_waiting(f"第 {round_count} 轮对话，正在思考或生成回答...")
        
        response = llm_client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools
        )

        message = response.choices[0].message
        messages.append(message)

        if response.choices[0].finish_reason != "tool_calls":
            display.display_info("对话完成，生成最终结果")
            return response.choices[0].message.content

        # 显示工具调用
        tool_call = response.choices[0].message.tool_calls[0]
        display.display_tool_call(
            tool_call.function.name,
            json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
        )

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
                    display.display_success(f"工具 '{tool_name}' 执行成功")
                except Exception as e:
                    output = f"工具执行失败: {str(e)}"
                    display.display_error(f"工具 '{tool_name}' 执行失败: {str(e)}")
            else:
                output = f"未知工具: {tool_name}"
                display.display_warning(f"未知工具调用: {tool_name}")
            
            if block.function.name == "todo":
                used_todo = True
                # 显示任务列表更新
                display.show_task_summary()
            rounds_since_todo = 0 if used_todo else rounds_since_todo + 1

            messages.append({
                "role": "tool",
                "tool_call_id": block.id,
                "name": tool_name,
                "content": output
            })


if __name__ == "__main__":
    input_query = sanitize_text(input("Enter your query: ").strip())
    result = agent_loop(input_query, tools_list)
    display = get_display()
    display.display_final_result(result)
    console.print()
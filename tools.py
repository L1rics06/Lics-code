import json

CHILD_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_bash",
            "description": "在终端中执行一段 bash 命令",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "需要执行的终端命令，例如 touch main.c 或 echo 'hello' > main.c"
                    }
                },
                "required": [
                    "command"
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "打开指定的文件",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "需要打开的文件相对路径，例如：./document.txt"
                    }
                },
                "required": [
                    "file_path"
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "向指定的文件中写入内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "需要写入文件相对路径，例如：./document.txt"
                    },
                    "content": {
                        "type": "string",
                        "description": "需要写入文件的内容，例如：这是一个测试文件。"
                    }
                },
                "required": [
                    "file_path",
                    "content"
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "append_file",
            "description": "向指定的文件中追加内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "需要追加的文件相对路径，例如：./document.txt"
                    },
                    "content": {
                        "type": "string",
                        "description": "需要追加到文件的内容，例如：这是一个测试文件。"
                    }
                },
                "required": [
                    "file_path",
                    "content"
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "todo",
            "description": "Update task list. Track progress on multi-step tasks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tasks": {
                        "type": "array",
                        "description": "完整的任务列表，每次调用需传入所有任务（包括未完成的和已完成的）",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {
                                    "type": "string",
                                    "description": "任务唯一标识符"
                                },
                                "text": {
                                    "type": "string",
                                    "description": "任务描述"
                                },
                                "status": {
                                    "type": "string",
                                    "enum": [
                                        "pending",
                                        "in_progress",
                                        "completed"
                                    ],
                                    "description": "任务状态：pending=待处理, in_progress=进行中, completed=已完成"
                                }
                            },
                            "required": [
                                "id",
                                "text",
                                "status"
                            ]
                        }
                    }
                },
                "required": [
                    "tasks"
                ]
            }
        }
    },{
        "type": "function",
        "function": {
            "name": "load_skill",
            "description": "加载指定技能的内容，技能文件位于 ./skills 目录下",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "需要加载的技能名称，对应 ./skills 目录下的子目录名称，例如：code_assistant"
                    }
                },
                "required": [
                    "skill_name"
                ]
            }
        }
    }
]

PARENT_TOOLS = CHILD_TOOLS + [
    {
        "type": "function",
        "function": {
            "name": "run_subagent",
            "description": "运行一个子智能体来完成特定的任务，子智能体可以调用上述工具来辅助完成任务",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "需要子智能体完成的任务描述，例如：请帮我创建一个包含 main 函数的 C 语言文件。"
                    }
                },
                "required": [
                    "prompt"
                ]
            }
        }
    }
]
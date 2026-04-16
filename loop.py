from openai import OpenAI
import yaml
import logging 
import json
import subprocess

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

with open("./config.yaml", "r") as f:
    config = yaml.safe_load(f)
    client = OpenAI(
        api_key = config["api_key"],
        base_url = config["base_url"]
    )
    model = config["model_name"]
    
with open("./tools.json", "r") as f:
    tools_list = json.load(f)


def agent_loop(query, tools):
    messages = [{"role": "user", "content": query}]
    while True:    
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools
        )
        logging.info("正在思考或生成回答...")
        
        message = response.choices[0].message
        messages.append(message)
        
        if response.choices[0].finish_reason != "tool_calls":
            return response.choices[0].message.content+" (Finish Reason: "+response.choices[0].finish_reason+")"
        
        logging.info("Tool calls detected, processing...")
        logging.info(f"Response content: {response.choices[0].message.content}")
        logging.info(f"Tool calls detected: {response.choices[0].message.tool_calls}")
        
        results = []
        for block in response.choices[0].message.tool_calls:
            tool_name = block.function.name
            arguments = json.loads(block.function.arguments)
        
        output = run_bash(arguments.get("command", ""))

        messages.append({
                        "role": "tool",
                        "tool_call_id": block.id,
                        "name": tool_name,
                        "content": output
                    })
            

def run_bash(comment):
    try:
        result = subprocess.run(
            comment, 
            shell=True, 
            check=True, 
            text=True   
        )
        output = result.stdout.strip()
        if not output:
             return "命令执行成功，无终端输出。"
        return output
        
    except subprocess.CalledProcessError as e:
        error_msg = f"命令执行失败。错误码: {e.returncode}\n错误信息: {e.stderr}"
        logging.error(f"❌ {error_msg}")
        return error_msg
    except Exception as e:
        return f"系统调用异常: {str(e)}"

    
if __name__ == "__main__":
    input_query = input("Enter your query: ")
    #to solve the problem of garbled characters
    clean_query = input_query.encode('utf-8', errors='surrogateescape').decode('utf-8', errors='replace')
    
    results = agent_loop(clean_query, tools_list)
    print("Final Result:", results)
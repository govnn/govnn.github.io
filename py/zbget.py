import asyncio
from aiohttp import ClientSession
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import subprocess
import json
import time
import os

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36"
}

driver = webdriver.Chrome(options=chrome_options)


# 获取当前脚本所在目录
#script_dir = os.path.dirname(os.path.abspath(__file__))



# 定义一个信号量，限制并发量为 3
semaphore = asyncio.Semaphore(3)

async def fetch(url, session, values, valid_values):
    async with semaphore:  # 使用信号量限制并发
        process = None
        try:
            cmd = ['ffprobe', '-v', 'error', '-print_format', 'json', '-show_streams', '-select_streams', 'v', url]
            process = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10)
            info = json.loads(stdout.decode())
            width = info['streams'][0]['width']
            height = info['streams'][0]['height']
            print(f"{url} 分辨率: {width}x{height}")
            for value in values:
                if value in url:
                    valid_values.add(value)
                    print(f"Valid value found: {value}")
            return True
        except asyncio.TimeoutError:
            if process:
                process.kill()
        except Exception as e:
            pass
        finally:
            if process:
                await process.wait()
        return False



async def process_file(file_name, session, h, values):  
    file_path_cm = f"c/cm{h}.txt"
    file_path_cn = f"c/cn{h}.txt"
    #file_path_cm = os.path.join("c", f"cm{h}.txt")
    #file_path_cn = os.path.join("c", f"cn{h}.txt")
    valid_values_cm = set()  # 有效 X 值集合（cm）
    valid_values_cn = set()  # 有效 X 值集合（cn）
    all_new_data = []  # 存储所有新数据的列表
    
    # 检查文件是否存在，如果不存在，则打印消息并返回
    if not os.path.exists(file_path_cm):
        print(f"未找到文件: {file_path_cm}")
        return None
    if not os.path.exists(file_path_cn):
        print(f"未找到文件: {file_path_cn}")
        return None
    
    # 同时打开 "cm{i}.txt" 和 "cn{i}.txt" 两个文件
    with open(file_path_cm, 'r', encoding='utf-8') as file_cm, open(file_path_cn, 'r', encoding='utf-8') as file_cn:
        lines_cm = file_cm.readlines()
        lines_cn = file_cn.readlines()
        
        tasks = []
        print(f"\n链接：")
        for lines, file_type, valid_values in zip((lines_cm, lines_cn), ("cm", "cn"), (valid_values_cm, valid_values_cn)):
            for line in lines:
                for value in values:
                    link = f"http://{value}{line.strip()}"
                    print(link)  # 打印生成的链接
                    tasks.append(fetch(link, session, values, valid_values))
                    if len(tasks) >= 100:
                        await asyncio.gather(*tasks)
                        tasks = []
        
        # 处理剩余的任务
        if tasks:
            await asyncio.gather(*tasks)
        
        # 读取相应的文件并执行后续任务
        file_to_read_cm = f"d/dm{h}"
        file_to_read_cn = f"d/dn{h}"
        
        new_data_cm = []
        new_data_cn = []
        
        if valid_values_cm:
            print(f"适合 cm{h}")
            print("有效的 X 值:", ", ".join(valid_values_cm))
            file_to_read = file_to_read_cm
            new_data_cm = await process_folder(file_to_read, valid_values_cm, h)
            
        if valid_values_cn:
            print(f"适合 cn{h}")
            print("有效的 X 值:", ", ".join(valid_values_cn))
            file_to_read = file_to_read_cn
            new_data_cn = await process_folder(file_to_read, valid_values_cn, h)
        
        all_new_data.extend(new_data_cm)
        all_new_data.extend(new_data_cn)

    return all_new_data

async def process_folder(file_name_to_read, valid_values, h):
    print("读取文件:", file_name_to_read)
    new_lines = []
    with open(file_name_to_read, 'r', encoding='utf-8') as file_to_read:
        for line in file_to_read:
            for value in valid_values:
                parts = line.strip().split(',')
                parts[1] = f"http://{value}{parts[1]}"
                new_line = ','.join(parts)
                new_lines.append(new_line)
                #print(new_line)  # 打印新生成的数据

    return new_lines






async def main():
    async with ClientSession() as session:
        urls = [
            "https://fofa.info/result?qbase64=IlNlcnZlcjogdWRweHkiICYmIHJlZ2lvbj0ic2hhbnhpIg==&page=1&page_size=20",
            "https://fofa.info/result?qbase64=IlNlcnZlcjogdWRweHkiICYmIHJlZ2lvbj0iZ3Vhbmdkb25nIg==&page=1&page_size=20",
            "https://fofa.info/result?qbase64=IlNlcnZlcjogdWRweHkiICYmIHJlZ2lvbj0ic2hhbmdoYWki&page=1&page_size=20",   # sh
            "https://fofa.info/result?qbase64=IlNlcnZlcjogdWRweHkiICYmIHJlZ2lvbj0iZ3Vhbmd4aSI=&page=1&page_size=20",
            "https://fofa.info/result?qbase64=IlNlcnZlcjogdWRweHkiICYmIHJlZ2lvbj0iemhlamlhbmci&page=1&page_size=20",
            "https://fofa.info/result?qbase64=IlNlcnZlcjogdWRweHkiICYmIHJlZ2lvbj0iYmVpamluZyI=&page=1&page_size=20",    # BJ
            "https://fofa.info/result?qbase64=IlNlcnZlcjogdWRweHkiICYmIHJlZ2lvbj0ic2ljaHVhbiI=&page=1&page_size=20",
            "https://fofa.info/result?qbase64=IlNlcnZlcjogdWRweHkiICYmIHJlZ2lvbj0iZnVqaWFuIg==&page=1&page_size=20",
            "https://fofa.info/result?qbase64=IlNlcnZlcjogdWRweHkiICYmIHJlZ2lvbj0iY2hvbmdxaW5nIg==&page=1&page_size=20",
            "https://fofa.info/result?qbase64=IlNlcnZlcjogdWRweHkiICYmIHJlZ2lvbj0iamlhbmdzdSI=&page=1&page_size=20",

            "https://fofa.info/result?qbase64=IlNlcnZlcjogdWRweHkiICYmIHJlZ2lvbj0ic2hhbmRvbmci&page=1&page_size=20",
            "https://fofa.info/result?qbase64=IlNlcnZlcjogdWRweHkiICYmIHJlZ2lvbj0iYW5odWki&page=1&page_size=20",
            "https://fofa.info/result?qbase64=IlNlcnZlcjogdWRweHkiICYmIHJlZ2lvbj0iaHVuYW4i&page=1&page_size=20",
            "https://fofa.info/result?qbase64=IlNlcnZlcjogdWRweHkiICYmIHJlZ2lvbj0iaHViZWki&page=1&page_size=20",
            "https://fofa.info/result?qbase64=IlNlcnZlcjogdWRweHkiICYmIHJlZ2lvbj0iU2hhYW54aSI=&page=1&page_size=20",
              
        ]
        all_new_data = []
        for h, url in enumerate(urls, 1):
            new_data = await fetch_and_process(url, session, h)
            all_new_data.extend(new_data)
        await write_to_file(all_new_data)

async def fetch_and_process(url, session, h):
    await open_website(url)
    values = await fetch_values()
    new_data = await process_file(f"cm{h}.txt", session, h, values)
    return new_data

async def open_website(url):
    driver.get(url)

async def fetch_values():
    elements = driver.find_elements(By.CSS_SELECTOR, ".hsxa-host a")
    values = set(element.text for element in elements)
    return values

async def write_to_file(all_new_data):
    output_folder = "e"
    output_file_path = f"{output_folder}/888"
    #output_file_path = os.path.join("e", "888")
    with open(output_file_path, "a", encoding="utf-8") as file:
        for line in all_new_data:
            file.write(line + "\n")

now = time.time()
asyncio.run(main())
driver.quit()

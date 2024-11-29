import asyncio
from aiohttp import ClientSession
import json
import os
import subprocess
import time


semaphore = asyncio.Semaphore(3)

async def fetch(url, session, values, valid_values):
    async with semaphore:  
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
            #print(f"Exception occurred: {e}")
        finally:
            if process:
                await process.wait()
        return False

async def process_file(file_name, session, h, values):  
    file_path_cm = f"c/cm{h}.txt"
    file_path_cn = f"c/cn{h}.txt"
    
    valid_values_cm = set()  # 有效 X 值集合（cm）
    valid_values_cn = set()  # 有效 X 值集合（cn）
    all_new_data = []

    if not os.path.exists(file_path_cm):
        raise FileNotFoundError(f"未找到文件: {file_path_cm}")
    if not os.path.exists(file_path_cn):
        raise FileNotFoundError(f"未找到文件: {file_path_cn}")

    with open(file_path_cm, 'r', encoding='utf-8') as file_cm, open(file_path_cn, 'r', encoding='utf-8') as file_cn:
        lines_cm = file_cm.readlines()
        lines_cn = file_cn.readlines()

        tasks = []
        print(f"\n链接：")
        for lines, file_type, valid_values in zip((lines_cm, lines_cn), ("cm", "cn"), (valid_values_cm, valid_values_cn)):
            for line in lines:
                for value in values:
                    link = f"http://{value}{line.strip()}"
                    print(link)
                    tasks.append(fetch(link, session, values, valid_values))
                    if len(tasks) >= 100:
                        await asyncio.gather(*tasks)
                        tasks = []

        if tasks:
            await asyncio.gather(*tasks)

        file_to_read_cm = f"d/dm{h}"
        file_to_read_cn = f"d/dn{h}"
        
        new_data_cm = []
        new_data_cn = []

        if valid_values_cm:
            print(f"适合 cm{h}")
            print("有效的 X 值:", ", ".join(valid_values_cm))
            new_data_cm = await process_folder(file_to_read_cm, valid_values_cm, h)
            
        if valid_values_cn:
            print(f"适合 cn{h}")
            print("有效的 X 值:", ", ".join(valid_values_cn))
            new_data_cn = await process_folder(file_to_read_cn, valid_values_cn, h)

        all_new_data.extend(new_data_cm)
        all_new_data.extend(new_data_cn)

    return all_new_data

async def process_folder(file_name_to_read, valid_values, h):
    #print("读取文件:", file_name_to_read)
    new_lines = []
    with open(file_name_to_read, 'r', encoding='utf-8') as file_to_read:
        for line in file_to_read:
            for value in valid_values:
                parts = line.strip().split(',')
                parts[1] = f"http://{value}{parts[1]}"
                new_line = ','.join(parts)
                new_lines.append(new_line)

    return new_lines

def load_values_from_file(file_path):
    print(f"正在打开文件: {file_path}")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件未找到: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    values = []
    batch = []
    for line in lines:
        line = line.strip()
        if line:
            batch.append(line)
        else:
            if batch:
                values.append(batch)
                batch = []
    if batch:
        values.append(batch)
    return values

async def main():

    data_file_path = f"e/ips"
    
    data_values = load_values_from_file(data_file_path)
    async with ClientSession() as session:
        all_new_data = []
        for h, batch_values in enumerate(data_values, 1):
            print(f"\n处理第 {h} 批数据：{batch_values}")
            new_data = await fetch_and_process(batch_values, session, h)
            all_new_data.extend(new_data)
        await write_to_file(all_new_data)

async def fetch_and_process(batch_values, session, h):
    new_data = await process_file(f"cm{h}.txt", session, h, batch_values)
    return new_data

async def write_to_file(all_new_data):
    output_file_path = f"e/888"
    mode = "w"
    
    with open(output_file_path, mode, encoding="utf-8") as file:
        for line in all_new_data:
            file.write(line + "\n")
            mode = "a"

now = time.time()
asyncio.run(main())

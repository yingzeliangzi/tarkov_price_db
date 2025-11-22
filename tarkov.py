import requests
import json
import os
import csv
import time

# 配置
API_URL = "https://api.eftarkov.com/dasha445566.php?id=9"
OUTPUT_DIR = "Tarkov_Data"
IMG_DIR = os.path.join(OUTPUT_DIR, "images")
TEMP_JSON_FILE = os.path.join(OUTPUT_DIR, "temp_data.json")

# 伪装成浏览器
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Connection": "keep-alive"
}

def init_dirs():
    if not os.path.exists(IMG_DIR):
        os.makedirs(IMG_DIR)
        print(f"已创建目录: {IMG_DIR}")

def download_json_data():
    """流式下载 JSON 数据到本地文件，避免内存溢出或连接中断"""
    print(f"正在尝试连接 API (流式下载模式)...")
    try:
        # stream=True 允许下载大文件
        with requests.get(API_URL, headers=HEADERS, stream=True, timeout=60) as r:
            r.raise_for_status()
            total_size = 0
            with open(TEMP_JSON_FILE, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    if chunk: 
                        f.write(chunk)
                        total_size += len(chunk)
            print(f"JSON 数据下载完成，大小: {total_size / 1024 / 1024:.2f} MB")
            return True
    except Exception as e:
        print(f"API 下载失败: {e}")
        print("提示：如果API持续报错，请手动在浏览器打开链接，将内容另存为 'temp_data.json' 放入 Tarkov_Data 文件夹中。")
        return False

def load_local_json():
    """读取本地 JSON 文件"""
    if not os.path.exists(TEMP_JSON_FILE):
        print(f"错误：找不到数据文件 {TEMP_JSON_FILE}")
        return None
    
    print("正在解析本地 JSON 文件...")
    try:
        with open(TEMP_JSON_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"JSON 解析失败，文件可能不完整: {e}")
        return None

def get_best_trader_price(trader_prices):
    if not trader_prices:
        return 0, "无"
    max_price = 0
    best_trader = "无"
    for tp in trader_prices:
        price = tp.get('priceRUB', 0)
        if price > max_price:
            max_price = price
            best_trader = tp.get('trader', {}).get('name', 'Unknown')
    return max_price, best_trader

def download_image(url, file_name):
    path = os.path.join(IMG_DIR, file_name)
    if os.path.exists(path):
        return path 
    
    try:
        # 图片下载也加上 User-Agent
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            with open(path, 'wb') as f:
                f.write(resp.content)
            return path
    except Exception:
        pass # 图片下载失败不报错，保持静默
    return None

def generate_html(processed_data):
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>塔科夫离线物价表</title>
        <style>
            /* 核心布局：让页面充满屏幕，且不出现双重滚动条 */
            body { 
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif; 
                background-color: #121212; 
                color: #e0e0e0; 
                margin: 0; 
                padding: 0; 
                height: 100vh; /* 强制全屏高度 */
                display: flex;
                flex-direction: column; /* 垂直排列：头部在上，表格在下 */
                overflow: hidden; /* 禁止 body 滚动，只让表格区域滚动 */
            }

            /* 1. 顶部固定区域 (标题 + 搜索) */
            .fixed-header { 
                flex: 0 0 auto; /* 不允许压缩或拉伸 */
                background: #1f1f1f; 
                border-bottom: 1px solid #333; 
                padding: 20px 30px; 
                z-index: 20;
                box-shadow: 0 4px 8px rgba(0,0,0,0.4);
            }

            .header-title {
                margin: 0 0 15px 0;
                font-size: 1.5rem;
                font-weight: bold;
                color: #fff;
            }

            input#searchInput { 
                width: 100%; 
                max-width: 800px;
                padding: 12px 15px; 
                font-size: 16px; 
                border: 1px solid #444; 
                background: #2d2d2d; 
                color: white; 
                border-radius: 6px; 
                outline: none;
                transition: border 0.2s, background 0.2s;
            }
            input#searchInput:focus {
                border-color: #4ec9b0;
                background: #333;
            }

            /* 2. 表格滚动区域 */
            .table-scroll-container {
                flex: 1 1 auto; /* 占据剩余所有空间 */
                overflow-y: auto; /* 关键：只在这里开启垂直滚动 */
                padding: 0 30px;
                position: relative;
            }

            table { 
                width: 100%; 
                border-collapse: separate; 
                border-spacing: 0;
                margin-top: 0; 
            }

            /* 3. 表头 - 永远吸附在滚动容器顶部 (Top: 0) */
            th { 
                position: sticky; 
                top: 0; /* 因为容器独立滚动，所以这里填 0 即可，不用算高度 */
                z-index: 10; 
                background-color: #121212; 
                text-align: left; 
                padding: 15px 10px; 
                border-bottom: 2px solid #333; 
                font-weight: 600;
                color: #bbb;
                box-shadow: 0 2px 0px rgba(0,0,0,0.2);
            }

            td { 
                padding: 12px 10px; 
                border-bottom: 1px solid #252525; 
                vertical-align: middle; 
            }
            
            tr:hover { background-color: #1e1e20; }

            /* 数据样式 */
            .price-rub { font-family: 'Consolas', monospace; font-size: 1.1em; letter-spacing: 0.5px; }
            .price-rub::after { content: " ₽"; color: #666; font-size: 0.8em; }
            
            .diff-pos { color: #4ec9b0; font-weight: bold; } 
            .diff-neg { color: #f44747; font-weight: bold; } 

            /* 图片样式 */
            img.item-icon { 
                width: 56px; 
                height: 56px; 
                object-fit: contain; 
                background: #000; 
                border-radius: 4px; 
                border: 1px solid #333; 
                display: block;
            }

            .trader-tag { 
                font-size: 0.8em; 
                color: #aaa; 
                background: #333; 
                padding: 2px 6px; 
                border-radius: 4px; 
                margin-left: 8px; 
            }
            
            .item-meta { font-size: 0.85em; color: #777; margin-top: 4px; }
        </style>
    </head>
    <body>
        <div class="fixed-header">
            <div class="header-title">Escape from Tarkov 离线物价表</div>
            <input type="text" id="searchInput" placeholder="搜索物品名称 (例如: M4A1, 钥匙)..." autocomplete="off">
        </div>

        <div class="table-scroll-container">
            <table id="itemTable">
                <thead>
                    <tr>
                        <th width="70">图示</th>
                        <th>物品信息</th>
                        <th>基准价格</th>
                        <th>跳蚤市场</th>
                        <th>商人收购 (最高)</th>
                        <th>差价 (跳蚤-商人)</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    print("正在生成 HTML (Flex布局版)...")
    for p in processed_data:
        flea_display = f"{p['flea_price']:,}" if p['flea_price'] > 0 else "-"
        diff_class = "diff-pos" if p['raw_diff'] > 0 else "diff-neg"
        
        html_content += f"""
            <tr>
                <td><img src="{p['img_path']}" loading="lazy" class="item-icon" onerror="this.style.display='none'"></td>
                <td>
                    <div style="font-size:1em; font-weight:bold; color:#ddd;">{p['name']}</div>
                    <div class="item-meta">{p['short_name']}</div>
                </td>
                <td class="price-rub">{p['base_price']:,}</td>
                <td class="price-rub" style="color:#a5d6ff;">{flea_display}</td>
                <td>
                    <span class="price-rub">{p['trader_price']:,}</span>
                    <span class="trader-tag">{p['best_trader']}</span>
                </td>
                <td class="{diff_class}">{p['diff']}</td>
            </tr>
        """

    html_content += """
                </tbody>
            </table>
        </div>
        <script>
            const searchInput = document.getElementById('searchInput');
            const table = document.getElementById('itemTable');
            let timeout = null;

            searchInput.addEventListener('input', function() {
                clearTimeout(timeout);
                timeout = setTimeout(() => {
                    const filter = searchInput.value.toLowerCase().trim();
                    const rows = table.getElementsByTagName('tr');
                    
                    requestAnimationFrame(() => {
                        // 从索引 1 开始 (跳过 thead)
                        for (let i = 1; i < rows.length; i++) {
                            const row = rows[i];
                            const nameCol = row.getElementsByTagName('td')[1];
                            
                            if (nameCol) {
                                const fullName = nameCol.getElementsByTagName('div')[0].textContent.toLowerCase();
                                const shortName = nameCol.getElementsByTagName('div')[1].textContent.toLowerCase();
                                
                                if (fullName.includes(filter) || shortName.includes(filter)) {
                                    row.style.display = "";
                                } else {
                                    row.style.display = "none";
                                }
                            }
                        }
                    });
                }, 200);
            });
        </script>
    </body>
    </html>
    """
    
    html_path = os.path.join(OUTPUT_DIR, "index.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

def main():
    init_dirs()
    
    # 步骤 1: 获取数据 (优先下载，如果已存在且不想重复下载可注释掉 download 这一行)
    if not os.path.exists(TEMP_JSON_FILE):
        success = download_json_data()
        if not success:
            return
    else:
        print(f"检测到已存在本地数据文件: {TEMP_JSON_FILE}，跳过下载直接使用。")
        # 如果你想强制重新下载，请手动删除 Tarkov_Data 文件夹里的 temp_data.json
    
    # 步骤 2: 解析数据
    data = load_local_json()
    if not data: return

    items = data.get("raw_api_data", {}).get("data", {}).get("items", [])
    print(f"开始处理 {len(items)} 个物品...")

    processed_data = []
    
    # 步骤 3: 处理每一项
    for idx, item in enumerate(items):
        item_id = item.get('id')
        if not item_id: continue

        # 提取价格
        base_price = item.get('basePrice', 0)
        flea_price = item.get('lastLowPrice') or 0
        trader_price, best_trader_name = get_best_trader_price(item.get('traderPrices', []))
        
        # 逻辑计算
        diff = flea_price - trader_price if (flea_price and trader_price) else 0
        diff_display = f"{diff:,}"
        if flea_price == 0: diff_display = "无跳蚤价"
        elif trader_price == 0: diff_display = "仅跳蚤"

        # 图片处理
        img_filename = f"{item_id}.webp"
        icon_url = item.get('iconLink')
        local_img_path = f"images/{img_filename}" # HTML相对路径
        
        # 仅在图片文件不存在时下载
        if icon_url:
            download_image(icon_url, img_filename)
        
        processed_data.append({
            "img_path": local_img_path,
            "name": item.get('name', 'Unknown'),
            "short_name": item.get('shortName', ''),
            "base_price": base_price,
            "flea_price": flea_price,
            "offer_count": item.get('lastOfferCount', 0),
            "trader_price": trader_price,
            "best_trader": best_trader_name,
            "diff": diff_display,
            "raw_diff": diff
        })
        
        if (idx + 1) % 100 == 0:
            print(f"进度: {idx + 1}/{len(items)}")

    # 步骤 4: 生成文件
    # CSV
    csv_path = os.path.join(OUTPUT_DIR, "tarkov_prices.csv")
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(["简称", "全名", "基准价", "跳蚤价", "商人收购价", "收购商人", "差价"])
        for p in processed_data:
            writer.writerow([p['short_name'], p['name'], p['base_price'], p['flea_price'], p['trader_price'], p['best_trader'], p['raw_diff']])
    
    # HTML
    generate_html(processed_data)
    print(f"\n全部完成！\n1. 网页位置: {os.path.join(OUTPUT_DIR, 'index.html')}\n2. 表格位置: {csv_path}")

if __name__ == "__main__":
    main()
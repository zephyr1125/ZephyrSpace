"""
Phase 1: Mechanical formatting - image paths, HTML tables, frontmatter, heading cleanup.
Complex text restructuring done manually afterwards.
"""
import re
from pathlib import Path

VAULT = Path(r"E:\ObsidianVaults\ZephyrSpace")
MD_PATH = VAULT / "Clippings/方正证券-国防军工行业：即将进入全面复苏阶段，把握新质战斗力及军贸两大主线-260603.md"
IMG_DIR = "方正证券-国防军工行业：即将进入全面复苏阶段，把握新质战斗力及军贸两大主线-260603_images"

with open(MD_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# Step 1: Fix image paths
content = content.replace('](images/', f']({IMG_DIR}/')

# Step 2: Convert HTML tables to Markdown
def html_table_to_md(html):
    rows = []
    for tr in re.findall(r'<tr>(.*?)</tr>', html, re.DOTALL):
        cells = []
        for td in re.findall(r'<td[^>]*>(.*?)</td>', tr, re.DOTALL):
            cell = td.strip()
            cell = cell.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
            cell = re.sub(r'<[^>]+>', '', cell)
            cell = ' '.join(cell.split())
            cells.append(cell)
        if cells:
            rows.append(cells)
    if not rows:
        return html
    lines = []
    lines.append('| ' + ' | '.join(rows[0]) + ' |')
    lines.append('|' + '|'.join([' --- ' for _ in rows[0]]) + '|')
    for row in rows[1:]:
        while len(row) < len(rows[0]):
            row.append('')
        lines.append('| ' + ' | '.join(row[:len(rows[0])]) + ' |')
    return '\n'.join(lines)

content = re.sub(r'<table>.*?</table>', lambda m: html_table_to_md(m.group(0)), content, flags=re.DOTALL)

# Step 3: Build YAML frontmatter + remove original header
frontmatter = """---
title: 国防军工行业中期策略——即将进入全面复苏阶段
subtitle: 把握新质战斗力及军贸两大主线
source: 方正证券
date: 2026-06-03
analyst:
  - 李鲁靖
  - 黄凯伦
  - 刘明洋
  - 张世朴
tags:
  - 行业研究
  - 国防军工
  - 军贸
  - 新质战斗力
type: 券商研报
created: 2026-06-07
---

> **方正证券 | 航空航天与防务团队 | 中期行业策略报告**
> 分析师：李鲁靖 S1220523090002 | 黄凯伦 S1220524090001 | 刘明洋 S1220524010002 | 张世朴 S1220525100001

---

"""

# Find where to cut the original header
lines = content.split('\n')
content_start = 0
for i, line in enumerate(lines):
    if i > 5 and line.startswith('## '):
        content_start = i
        break

if content_start > 0:
    content = '\n'.join(lines[content_start:])
else:
    content = '\n'.join(lines)

content = frontmatter + content

# Step 4: Fix scattered single-char lines from diagram OCR
content = re.sub(r'\n战\n术\n体\n系\n发\n展\n', '\n**战术体系发展**：', content)
content = re.sub(r'\n装\n备\n体\n系\n发\n展\n', '\n**装备体系发展**：', content)

# Step 5: Fix heading hierarchy
# Demote sub-sections from ## to ###
subsections_to_demote = [
    '无人僚机优势', '战场实际应用', '分工明确，效率倍增', '人机融合，加快决策',
    '高度智能，应用广泛', '战略规划方面', '模块化趋势', '新型号批产',
    '紧迫性', '爆发性', '持续性', '军民融合性',
    '综合态势感知能力', '指挥控制能力', '隐蔽突防和打击能力',
    '水下防御作战能力', '水下信息作战能力', '综合保障能力',
    '机动装备', '固定装备', '基础设施',
    '分析师声明', '免责声明', '方正证券研究所',
    '近期目标', '中期目标', '远期目标',
]
for s in subsections_to_demote:
    content = re.sub(rf'\n## {s}\n', rf'\n### {s}\n', content)

# Fix numbered AI sub-sections
ai_fixes = {
    '①态势感知：穿透战场迷雾，构建非对称优势': '### 态势感知：穿透战场迷雾，构建非对称优势',
    '②指挥控制：重塑决策模式，夺取速度优势': '### 指挥控制：重塑决策模式，夺取速度优势',
    '③武器打击：增强体系韧性，保证持续作战': '### 武器打击：增强体系韧性，保证持续作战',
    '④战场互联：自由互联互通，实现网络优势': '### 战场互联：自由互联互通，实现网络优势',
    '⑤支援保障：创新训练模式，优化后勤保障': '### 支援保障：创新训练模式，优化后勤保障',
}
for old, new in ai_fixes.items():
    content = content.replace(f'## {old}', new)

# Fix chapter numbers
content = re.sub(r'## 第一章\b', '## 一、', content)
content = re.sub(r'## 第二章\b', '## 二、', content)
content = re.sub(r'## 第三章\b', '## 三、', content)

# Fix "➢ 内需" and "外贸" as sub-headings
content = re.sub(r'## ➢ 内需：', '#### 内需：', content)
content = re.sub(r'## 外贸：', '#### 外贸：', content)
content = re.sub(r'## • 需求端：', '##### 需求端：', content)
content = re.sub(r'## • 供给端：', '##### 供给端：', content)

# Write output
with open(MD_PATH, 'w', encoding='utf-8') as f:
    f.write(content)

print("Phase 1 complete: image paths, HTML tables, frontmatter, heading cleanup")
print(f"Output: {MD_PATH}")

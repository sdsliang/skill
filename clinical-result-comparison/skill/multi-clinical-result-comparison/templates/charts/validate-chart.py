#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate-chart.py — Tool Smith 图表产物自检（生成后必跑；失败即修复后重跑）

校验 multi-clinical-result-comparison skill 产出的图表 HTML fragment，
检查项对齐 Tool Smith 真实契约 + 历史线上事故根因（脚本填充 CHART 时
双 '{' / 丢结尾分号）。

用法:
  python3 validate-chart.py <file.html> [file.html ...]
  python3 validate-chart.py <dir>              # 递归扫描目录内 *.html

退出码: 0 = 全部通过; 1 = 存在错误; 2 = 用法错误
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

MAX_SIZE = 1 << 20  # 1 MiB（Tool Smith 上限）

# Tool Smith 前端子串校验：lower.includes(...)，对全文（含注释/CSS/script 字符串）任意位置命中即拒绝
FORBIDDEN = ["<!doctype", "<html", "<head", "<body", "<meta", "<title"]
# 含 <head 前缀的标签同样命中 '<head' 子串，单独提示
FORBIDDEN_TAGS = ["<header", "<head>", "<head "]

COMMENT_RE = re.compile(r"<!--[\s\S]*?-->")
SCRIPT_RE = re.compile(r"<script(?:\s[^>]*)?>([\s\S]*?)</script>", re.IGNORECASE)
CHART_RE = re.compile(r"\bconst\s+CHART\s*=\s*\{")
DOUBLE_BRACE_RE = re.compile(r"\bconst\s+CHART\s*=\s*\{\s*\{")
FIELDS_RE = re.compile(r"""["']?(?:bars|points|events|series)["']?\s*[:=]""")
TITLE_RE = re.compile(r"""["']?title["']?\s*[:=]""")


def first_line(raw, idx):
    return raw[:idx].count("\n") + 1


def check_fragment(raw, problems):
    """Tool Smith 结构 + 禁用子串硬校验。"""
    low = raw.lower()
    stripped = raw.strip()
    if not stripped.startswith("<"):
        problems.append("文件不以 '<' 开头，不是有效的 HTML/SVG fragment")
    if stripped.startswith("<svg"):
        problems.append("以 '<svg' 开头（SVG 类型）；本项目图表应为 HTML fragment（<style>+内容+<script>）")
    for s in FORBIDDEN:
        idx = low.find(s)
        if idx >= 0:
            problems.append("含禁用子串 '%s'（第 %d 行，全文任意位置命中即被 Tool Smith 拒绝）"
                            % (s, first_line(raw, idx)))
    for s in FORBIDDEN_TAGS:
        idx = low.find(s)
        if idx >= 0:
            problems.append("含禁止标签子串 '%s'（第 %d 行，命中 '<head' 前缀）——不要用 <header> 等，用 <div class=\"header\">"
                            % (s, first_line(raw, idx)))


def find_chart_end(script, start_brace):
    """从 CHART 起始 '{' 做括号配对，返回闭合 '}' 的下标；不配对返回 -1。"""
    depth = 0
    in_str = None
    i = start_brace
    n = len(script)
    while i < n:
        c = script[i]
        if in_str:
            if c == "\\":
                i += 2
                continue
            if c == in_str:
                in_str = None
        else:
            if c in "'\"`":
                in_str = c
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    return -1


def check_script(script, raw, problems):
    """CHART 结构与 JS 语法校验（本次线上事故根因重点）。"""
    m = CHART_RE.search(script)
    if not m:
        problems.append("脚本内未找到 'const CHART = {'")
        return
    line = script[: m.start()].count("\n") + 1

    # 事故根因 ①：双 '{'
    if DOUBLE_BRACE_RE.search(script):
        problems.append("CHART 双左花括号（'const CHART = {' 后紧跟 '{'，第 %d 行）：模板已带 '{'，"
                        "数据对象（JSON/Python dict）不要再拼一个 '{' → 运行时报 Unexpected token '{'" % line)

    # 事故根因 ②：结尾分号
    brace = m.end() - 1  # 指向 '{'
    end = find_chart_end(script, brace)
    if end < 0:
        problems.append("CHART 花括号不配对（第 %d 行起），数据对象未闭合" % line)
        return
    k = end + 1
    while k < len(script) and script[k] in " \t\r\n":
        k += 1
    if k >= len(script) or script[k] != ";":
        problems.append("CHART 对象未以 '};' 结尾（第 %d 行附近）：缺分号会被 ASI 与下一行 "
                        "'(function(){…})()' 连读成“调用对象”→ 运行时 TypeError: … is not a function。"
                        "请保留模板的 '};'" % script[:end].count("\n"))

    # 基本字段
    if not TITLE_RE.search(script):
        problems.append("CHART 缺少 title 字段")
    if not FIELDS_RE.search(script):
        problems.append("CHART 缺少数据字段：bars（柱）/ series+points（折线）/ events（时间轴）")


def check_js_syntax(script, problems):
    """node 可用时做真正 JS 语法校验；不可用时靠上方启发式兜底。"""
    node = shutil.which("node")
    if not node or not script.strip():
        return
    fd, tpath = tempfile.mkstemp(suffix=".js", prefix="chart-check-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tf:
            tf.write(script)
        r = subprocess.run([node, "--check", tpath], capture_output=True, text=True)
        if r.returncode != 0:
            err = (r.stderr or "").strip()
            lines = err.splitlines()
            msg = next((ln.strip() for ln in lines if re.search(r"Error:|SyntaxError", ln)),
                       lines[-1] if lines else "unknown")
            # 行号：node 会输出 <tmpfile>:N 或 /tmp/...:N
            mline = re.search(r":(\d+)(?::\d+)?\s*$", lines[0] if lines else "", re.M) \
                or re.search(r"%s:(\d+)" % re.escape(tpath), err, re.M)
            loc = "（脚本第 %s 行）" % mline.group(1) if mline else ""
            problems.append("JS 语法校验失败 (node --check)%s: %s" % (loc, msg))
    finally:
        os.unlink(tpath)


def validate(path):
    problems = []
    try:
        with open(path, encoding="utf-8") as fh:
            raw = fh.read()
    except Exception as e:  # noqa: BLE001
        print("   ✗ 无法读取文件: %s" % e)
        return False

    size = os.path.getsize(path)
    if size > MAX_SIZE:
        problems.append("文件过大 %d B > 1 MiB（Tool Smith 上限）" % size)

    check_fragment(raw, problems)

    # 提取 <script>（先剥 HTML 注释，避免注释里的 <script> 字面量干扰）
    body = COMMENT_RE.sub("", raw)
    scripts = SCRIPT_RE.findall(body)
    if not scripts:
        problems.append("未找到 <script> 块（fragment 应为 <style> + 内容 + <script>）")
    else:
        script = scripts[0]
        check_script(script, raw, problems)
        check_js_syntax(script, problems)

    for p in problems:
        print("   ✗ " + p)
    return not problems


def main():
    paths = sys.argv[1:]
    if not paths:
        print("用法: python3 validate-chart.py <file.html> [file.html ... | <dir>]")
        return 2
    files = []
    for p in paths:
        if os.path.isdir(p):
            for root, _, fs in os.walk(p):
                for f in sorted(fs):
                    if f.lower().endswith(".html"):
                        files.append(os.path.join(root, f))
        else:
            files.append(p)
    if not files:
        print("未找到任何 .html 文件")
        return 2
    fails = 0
    for f in files:
        ok = validate(f)
        print("PASS  " if ok else "FAIL  ", f)
        fails += 0 if ok else 1
    print("\n共 %d 个文件，%d 个未通过" % (len(files), fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""
Repland 答辩 deck —— SVG 生成框架
约束来源：ppt-master/references/shared-standards-core.md
  · 每个逻辑单元 = 一个顶层 <g id> + data-pptx-bounds
  · 顶层组之间不得重叠（>1px 判 fail）
  · 不用 class / <style> / mask / 渐变 / filter / 任意 transform
  · 多行文本用定位 tspan（x 重复父级，dy 为正）
"""
import json
import math
import pathlib

# ---------- 画布 ----------
W, H = 1280, 720

# ---------- 色板：纸面 + 墨绿 + 单一 amber 语义 ----------
PAPER  = "#F2F4EF"
CARD   = "#FFFFFF"
INK    = "#071A14"
INK2   = "#1A6B52"
INK3   = "#3E5C50"
MUTED  = "#6B7C74"
HAIR   = "#D3D1C7"
HAIR2  = "#E6E4DA"
AMBER  = "#B87824"
AMBERB = "#FBF3E4"
ROSE   = "#9B4A4A"
DARK   = "#0B221B"

SANS  = "Noto Sans SC"
SERIF = "Noto Serif SC"
MONO  = "Consolas"

# ---------- 版面常量 ----------
ML, MR = 80, 1200          # 内容左右边界
BODY_T, BODY_B = 186, 626  # 正文区上下
FOOT_Y = 678


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def tw(s, fs, mono=False):
    """估算文本宽度（px）。中文按 1em，西文按 0.55em。"""
    w = 0.0
    for ch in s:
        o = ord(ch)
        if o > 0x2E80:               # CJK / 全角
            w += 1.0
        elif ch in "ilj.,:;'|!":     # 窄字符
            w += 0.30
        elif ch.isupper() or ch.isdigit():
            w += 0.62
        else:
            w += 0.55
    return w * fs * (1.02 if mono else 1.0)


def wrap(s, fs, maxw, mono=False):
    """按宽度折行；中文可逐字断，西文按词断。"""
    lines, cur = [], ""
    for ch in s:
        trial = cur + ch
        if tw(trial, fs, mono) > maxw and cur:
            # 西文回退到词边界
            if ch.isascii() and ch not in "，。、；：）》」』":
                cut = max(cur.rfind(" "), cur.rfind("/"))
                if cut > len(cur) * 0.5:
                    lines.append(cur[:cut])
                    cur = cur[cut + 1:] + ch
                    continue
            lines.append(cur)
            cur = ch
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def text_block(x, y, s, fs, fill=INK, family=SANS, maxw=None, lh=1.55,
               weight="normal", anchor="start", mono=False, opacity=None):
    """多行文本：首行直出，后续定位 tspan。返回 svg 片段。"""
    dy = round(fs * lh, 1)
    lines = wrap(s, fs, maxw, mono) if maxw else [s]
    op = f' opacity="{opacity}"' if opacity else ""
    head = (f'<text x="{x}" y="{y}" font-family="{family}" font-size="{fs}" '
            f'fill="{fill}" font-weight="{weight}" text-anchor="{anchor}"{op}>')
    body = esc(lines[0])
    for ln in lines[1:]:
        body += f'<tspan x="{x}" dy="{dy}">{esc(ln)}</tspan>'
    return head + body + "</text>"


class Page:
    def __init__(self, name, kicker, title, section="", dark=False, grad=None):
        self.name = name
        self.dark = dark
        self.grad = grad            # (c0, c1) 竖向双色渐变，替代纯色背景
        self.groups = []        # (gid, x, y, w, h, inner, anim)
        self.root = []          # 根级原子（role=decoration/background）
        self.head = (kicker, title, section)
        self.footer_note = ""
        self.footer_page = ""
        self.extra_defs = ""       # 额外 <defs> 内容（如文字渐变）

    # ---------- 根级装饰（不进动画） ----------
    def deco(self, inner, gid=None, role="decoration", bounds=(0, 0, W, H)):
        i = f' id="{gid}"' if gid else ""
        b = f' data-pptx-bounds="{bounds[0]} {bounds[1]} {bounds[2]} {bounds[3]}"'
        self.root.append(f'<g{i}{b} data-pptx-role="{role}">{inner}</g>')

    # ---------- 内容组（= 一个动画步） ----------
    def g(self, gid, x, y, w, h, inner, anim="fade", role=None):
        """role: 结构性 role（如 decoration）→ checker 豁免重叠，sidecar 仍可动画"""
        self.groups.append((gid, x, y, w, h, inner, anim, role))
        return gid

    # ---------- 校验 ----------
    def verify(self):
        errs = []
        gs = self.groups
        for i in range(len(gs)):
            a = gs[i]
            if a[1] < -1 or a[2] < -1 or a[1] + a[3] > W + 1 or a[2] + a[4] > H + 1:
                errs.append(f"[越界] {a[0]} bounds=({a[1]},{a[2]},{a[3]},{a[4]})")
            for j in range(i + 1, len(gs)):
                b = gs[j]
                if a[7] or b[7]:        # structural-role 组豁免（与 checker 一致）
                    continue
                ox = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
                oy = min(a[2] + a[4], b[2] + b[4]) - max(a[2], b[2])
                if ox > 1 and oy > 1:
                    errs.append(
                        f"[重叠] {a[0]} × {b[0]}  overlap={ox:.0f}×{oy:.0f}px")
        return errs

    # ---------- 输出 ----------
    def svg(self):
        kicker, title, section = self.head
        bg = PAPER if not self.dark else DARK
        out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
               f'width="{W}" height="{H}" lang="zh-CN" data-pptx-page-role="content" '
               f'font-family="{SANS}">']
        if self.grad:
            c0, c1 = self.grad
            out.append(f'<defs><linearGradient id="bgGrad" x1="0" y1="0" x2="0" y2="1">'
                       f'<stop offset="0" stop-color="{c0}"/>'
                       f'<stop offset="1" stop-color="{c1}"/></linearGradient>'
                       f'{self.extra_defs}</defs>')
            out.append(f'<rect id="bg" data-pptx-role="background" x="0" y="0" '
                       f'width="{W}" height="{H}" fill="url(#bgGrad)"/>')
        else:
            if self.extra_defs:
                out.append(f'<defs>{self.extra_defs}</defs>')
            bg = PAPER if not self.dark else DARK
            out.append(f'<rect id="bg" data-pptx-role="background" x="0" y="0" '
                       f'width="{W}" height="{H}" fill="{bg}"/>')
        out.extend(self.root)

        if title or kicker:
            tcol = "#F4F7F2" if self.dark else INK
            kcol = "#8FB3A4" if self.dark else INK3
            scol = "#7E9C8E" if self.dark else MUTED
            out.append(f'<g id="header" data-pptx-bounds="0 54 1280 108" '
                       f'data-pptx-role="header">')
            out.append(f'<text x="{ML}" y="82" font-family="{MONO}" font-size="14" '
                       f'fill="{kcol}" letter-spacing="2.4">{esc(kicker)}</text>')
            if title:
                out.append(f'<text x="{ML}" y="132" font-family="{SERIF}" font-size="38" '
                           f'fill="{tcol}">{esc(title)}</text>')
            if section:
                out.append(f'<text x="{MR}" y="82" font-family="{MONO}" font-size="13" '
                           f'fill="{scol}" text-anchor="end" letter-spacing="1.6">'
                           f'{esc(section)}</text>')
            out.append(f'<line x1="{ML}" y1="156" x2="{MR}" y2="156" '
                       f'stroke="{"#2E4A3E" if self.dark else HAIR}" stroke-width="1"/>')
            out.append("</g>")

        if self.footer_note or self.footer_page:
            fcol = "#7E9C8E" if self.dark else MUTED
            out.append(f'<g id="footer" data-pptx-bounds="0 658 1280 40" '
                       f'data-pptx-role="footer">')
            if self.footer_note:
                out.append(text_block(ML, FOOT_Y, self.footer_note, 13, fcol,
                                      MONO, maxw=980))
            if self.footer_page:
                out.append(f'<text x="{MR}" y="{FOOT_Y}" font-family="{MONO}" '
                           f'font-size="13" fill="{fcol}" text-anchor="end">'
                           f'{esc(self.footer_page)}</text>')
            out.append("</g>")

        for gid, x, y, w, h, inner, _, role in self.groups:
            r = f' data-pptx-role="{role}"' if role else ""
            out.append(f'<g id="{gid}" data-pptx-bounds="{x} {y} {w} {h}"{r}>'
                       f'{inner}</g>')
        out.append("</svg>")
        return "\n".join(out)


# ---------- 复用图元 ----------
def card(x, y, w, h, fill=CARD, stroke=HAIR, r=10, sw=1):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


def bar(x, y, w, h, fill, r=0):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}"/>'


def hline(x1, x2, y, col=HAIR, sw=1, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" '
            f'stroke="{col}" stroke-width="{sw}"{d}/>')


def vline(x, y1, y2, col=HAIR, sw=1, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" '
            f'stroke="{col}" stroke-width="{sw}"{d}/>')


def num(n, x, y, fs, fill=AMBER, anchor="start"):
    return (f'<text x="{x}" y="{y}" font-family="{MONO}" font-size="{fs}" '
            f'fill="{fill}" text-anchor="{anchor}">{n}</text>')


def polar(cx, cy, r, deg):
    a = math.radians(deg - 90)
    return cx + r * math.cos(a), cy + r * math.sin(a)


def arc(cx, cy, r, a0, a1):
    x0, y0 = polar(cx, cy, r, a0)
    x1, y1 = polar(cx, cy, r, a1)
    large = 1 if abs(a1 - a0) > 180 else 0
    sweep = 1 if a1 > a0 else 0
    return (f'M {x0:.2f} {y0:.2f} A {r} {r} 0 {large} {sweep} '
            f'{x1:.2f} {y1:.2f}')


def icon(name, x, y, size, fill):
    return (f'<use data-icon="tabler-filled/{name}" x="{x}" y="{y}" '
            f'width="{size}" height="{size}" fill="{fill}"/>')


def chip(x, y, label, fs=13, fill=INK3, bg=HAIR2, padx=10, h=26):
    w = tw(label, fs) + padx * 2
    return (f'<rect x="{x}" y="{y}" width="{w:.0f}" height="{h}" rx="{h/2}" fill="{bg}"/>'
            f'<text x="{x + w/2:.0f}" y="{y + h/2 + fs*0.36:.0f}" '
            f'font-family="{SANS}" font-size="{fs}" fill="{fill}" '
            f'text-anchor="middle">{esc(label)}</text>'), w

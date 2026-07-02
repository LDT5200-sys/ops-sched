"""Public Flask entry for the operations scheduling tool.

The Streamlit app remains the full internal UI. This lightweight entry reuses
the CP-SAT solver so Vercel can host a stable external link.
"""

from __future__ import annotations

from datetime import date, timedelta
from html import escape

from flask import Flask, request

from config import ASSIGNMENT_LABELS, DAY_NAMES, DEFAULT_STAFF
from config import AssignmentType


app = Flask(__name__)


CSS = """
:root{--bg:#f7f8fa;--panel:#fff;--ink:#20242a;--muted:#667085;--line:#d9dee7;--green:#1f7a42;--blue:#2454a6;--warn:#a15c00}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans SC",sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:28px 24px 48px}.top{display:flex;justify-content:space-between;gap:20px;align-items:flex-start;margin-bottom:22px}
h1{font-size:30px;line-height:1.2;margin:0 0 8px}.sub{color:var(--muted);font-size:15px}.grid{display:grid;grid-template-columns:330px 1fr;gap:18px;align-items:start}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:8px;box-shadow:0 1px 2px rgba(16,24,40,.04)}.box{padding:18px}
label{display:block;font-size:13px;color:#344054;font-weight:650;margin:14px 0 7px}input,textarea{width:100%;border:1px solid #cfd6e1;border-radius:6px;padding:10px 11px;font-size:14px;background:#fff}
textarea{min-height:96px;resize:vertical}.row{display:grid;grid-template-columns:1fr 1fr;gap:12px}.btn{width:100%;margin-top:18px;border:0;border-radius:6px;background:var(--green);color:white;padding:12px 14px;font-size:15px;font-weight:700;cursor:pointer}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:14px}.kpi{background:#f4f7fb;border:1px solid #e2e8f0;border-radius:7px;padding:12px}.kpi span{display:block;color:var(--muted);font-size:12px}.kpi b{font-size:20px}
table{width:100%;border-collapse:collapse;font-size:14px}th,td{border:1px solid var(--line);padding:9px 8px;text-align:center}th{background:#f1f4f8;color:#344054}td.name{text-align:left;font-weight:700;background:#fbfcfe}
.tag{display:inline-block;min-width:54px;border-radius:999px;padding:3px 8px;font-weight:650}.rest{background:#eef0f3}.early{background:#fff3bf}.mid{background:#dbeafe}.late{background:#eadcff}.office{background:#dff4e6}.external{background:#ffe4bf}
.msg{border-radius:7px;padding:12px 14px;margin-bottom:14px}.ok{background:#edf8f0;border:1px solid #b7e2c3;color:#14532d}.bad{background:#fff4ed;border:1px solid #ffd2b8;color:#8a3b12}
.copy{white-space:pre-wrap;background:#101828;color:#eef4ff;border-radius:7px;padding:14px;overflow:auto;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px;margin-top:14px}
@media(max-width:860px){.grid{grid-template-columns:1fr}.kpis{grid-template-columns:repeat(2,1fr)}.top{display:block}}
"""


def parse_names(raw: str) -> list[str]:
    names = [x.strip() for x in raw.replace("，", ",").split(",") if x.strip()]
    return names or DEFAULT_STAFF


def clamp_int(value: str, default: int, low: int, high: int) -> int:
    try:
        num = int(value)
    except (TypeError, ValueError):
        num = default
    return max(low, min(high, num))


def build_params(num_people: int, work_days: int, external_total: int):
    total_work = num_people * work_days
    shift_slots = 3 * 7
    target_office = total_work - shift_slots - external_total
    if target_office < 0:
        return None, target_office
    return {"target_office": target_office}, target_office


def quick_schedule(num_people: int, work_days: int, external_total: int, max_consecutive: int):
    """Fast deterministic scheduler for the public share page."""
    solution = {}
    remaining = [work_days] * num_people
    shift_counts = [0] * num_people
    consecutive = [0] * num_people
    prev = [None] * num_people
    shifts = [AssignmentType.EARLY, AssignmentType.MID, AssignmentType.LATE]

    for d in range(7):
        assigned_today = set()
        for t in shifts:
            candidates = []
            for p in range(num_people):
                if p in assigned_today or remaining[p] <= 0:
                    continue
                if t == AssignmentType.EARLY and prev[p] == AssignmentType.LATE:
                    continue
                if consecutive[p] >= max_consecutive:
                    continue
                candidates.append(p)
            if not candidates:
                return None
            p = min(candidates, key=lambda x: (shift_counts[x], consecutive[x], remaining[x], x))
            solution[(p, d)] = t
            remaining[p] -= 1
            shift_counts[p] += 1
            assigned_today.add(p)

        for p in range(num_people):
            if (p, d) in solution:
                consecutive[p] += 1
                prev[p] = solution[(p, d)]
            else:
                prev[p] = None

    external_left = external_total
    office_left = sum(remaining) - external_left
    if office_left < 0:
        return None

    for d in range(7):
        for p in range(num_people):
            if (p, d) in solution:
                continue
            if remaining[p] <= 0 or consecutive[p] >= max_consecutive:
                solution[(p, d)] = AssignmentType.REST
                consecutive[p] = 0
                continue
            if external_left > 0:
                solution[(p, d)] = AssignmentType.EXTERNAL
                external_left -= 1
                remaining[p] -= 1
                consecutive[p] += 1
            elif office_left > 0 and d not in {5, 6}:
                solution[(p, d)] = AssignmentType.OFFICE
                office_left -= 1
                remaining[p] -= 1
                consecutive[p] += 1
            else:
                solution[(p, d)] = AssignmentType.REST
                consecutive[p] = 0

    # If weekend office avoidance left office days unfilled, use available rest days.
    for d in range(7):
        for p in range(num_people):
            if office_left <= 0:
                break
            if solution[(p, d)] == AssignmentType.REST and remaining[p] > 0:
                solution[(p, d)] = AssignmentType.OFFICE
                remaining[p] -= 1
                office_left -= 1
        if office_left <= 0:
            break

    return solution if external_left == 0 and office_left == 0 else None


def week_days(start: date) -> list[str]:
    return [(start + timedelta(days=i)).strftime("%m/%d") for i in range(7)]


def render_table(solution, names: list[str], week_start: date) -> str:
    label_class = {
        "休息": "rest",
        "早班": "early",
        "中班": "mid",
        "晚班": "late",
        "坐班": "office",
        "外派": "external",
    }
    head = "".join(f"<th>{DAY_NAMES[i]}<br>{week_days(week_start)[i]}</th>" for i in range(7))
    rows = []
    for p, name in enumerate(names):
        cells = []
        for d in range(7):
            label = ASSIGNMENT_LABELS[solution[(p, d)]]
            cls = label_class.get(label, "")
            cells.append(f'<td><span class="tag {cls}">{escape(label)}</span></td>')
        rows.append(f'<tr><td class="name">{escape(name)}</td>{"".join(cells)}</tr>')
    return f"<table><thead><tr><th>人员</th>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def copy_text(solution, names: list[str], week_start: date) -> str:
    lines = ["人员\t" + "\t".join(f"{DAY_NAMES[i]} {week_days(week_start)[i]}" for i in range(7))]
    for p, name in enumerate(names):
        row = [name]
        for d in range(7):
            row.append(ASSIGNMENT_LABELS[solution[(p, d)]])
        lines.append("\t".join(row))
    return "\n".join(lines)


@app.route("/", methods=["GET", "POST"])
def index():
    today = date.today()
    monday = today - timedelta(days=today.weekday())

    form = request.form if request.method == "POST" else {}
    names = parse_names(form.get("names", ", ".join(DEFAULT_STAFF)))
    week_start_raw = form.get("week_start", monday.isoformat())
    try:
        picked = date.fromisoformat(week_start_raw)
    except ValueError:
        picked = monday
    week_start = picked - timedelta(days=picked.weekday())
    work_days = clamp_int(form.get("work_days"), 5, 3, 7)
    external_total = clamp_int(form.get("external_total"), 0, 0, 7)
    max_consecutive = clamp_int(form.get("max_consecutive"), 5, 3, 7)

    result_html = ""
    if request.method == "POST":
        params, target_office = build_params(len(names), work_days, external_total)
        if len(names) < 4:
            result_html = '<div class="msg bad">在岗人数太少，至少建议 4 人以上再生成排班。</div>'
        elif params is None:
            result_html = (
                f'<div class="msg bad">人手不足：总工作天不足以覆盖 21 个跟播班次'
                f'和 {external_total} 天外派，请增加人数/工作天数或减少外派。</div>'
            )
        else:
            solution = quick_schedule(len(names), work_days, external_total, max_consecutive)
            if not solution:
                result_html = '<div class="msg bad">没有找到可行排班，请放宽连续工作、外派或工作天数约束。</div>'
            else:
                result_html = f"""
                <div class="msg ok">已生成可行排班，坐班自动配平为 {target_office} 天。</div>
                <div class="kpis">
                  <div class="kpi"><span>在岗人数</span><b>{len(names)}</b></div>
                  <div class="kpi"><span>跟播班次</span><b>21</b></div>
                  <div class="kpi"><span>坐班天数</span><b>{target_office}</b></div>
                  <div class="kpi"><span>外派天数</span><b>{external_total}</b></div>
                </div>
                {render_table(solution, names, week_start)}
                <div class="copy">{escape(copy_text(solution, names, week_start))}</div>
                """

    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>运营跟播排班系统</title><style>{CSS}</style></head><body>
    <main class="wrap">
      <div class="top"><div><h1>运营跟播排班系统</h1>
      <div class="sub">AI 自动排班 · 早/中/晚三班覆盖 · 坐班与外派自动配平</div></div></div>
      <div class="grid">
        <form class="panel box" method="post">
          <label>在岗人员（逗号分隔）</label>
          <textarea name="names">{escape(", ".join(names))}</textarea>
          <label>排班周（任意选择该周日期）</label>
          <input type="date" name="week_start" value="{week_start.isoformat()}">
          <div class="row">
            <div><label>每人工作天数</label><input name="work_days" type="number" min="3" max="7" value="{work_days}"></div>
            <div><label>外派总天数</label><input name="external_total" type="number" min="0" max="7" value="{external_total}"></div>
          </div>
          <label>最大连续工作天数</label>
          <input name="max_consecutive" type="number" min="3" max="7" value="{max_consecutive}">
          <button class="btn" type="submit">生成排班</button>
        </form>
        <section class="panel box">
          {result_html or '<div class="msg ok">填写左侧参数后生成排班。默认人员已按当前团队配置填入。</div>'}
        </section>
      </div>
    </main></body></html>"""

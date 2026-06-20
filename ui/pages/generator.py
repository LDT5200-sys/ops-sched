"""排班生成 — 主页面（重新设计的布局）。

改动仅限交互与版式；求解器调用 build_and_solve / validate_schedule、
参数字典结构、数据库写入逻辑均与原版一致。
"""

import json
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from database.engine import init_db, get_session
from database.crud import (
    seed_staff, get_active_staff, get_prev_schedule,
    save_schedule, get_external_history,
)
from solver.engine import build_and_solve, validate_schedule
from solver.balance import compute_balance_targets
from config import AssignmentType, ASSIGNMENT_LABELS, DAY_NAMES, SHIFT_TYPES
from ui.styles import apply_styles, page_header, section_title, kpi_row, note, divider
from ui.components.schedule_grid import (
    render_readonly_grid, render_schedule_editor, render_entries_grid,
    render_traditional_grid, build_traditional_text,
)
from ui.components.summary_cards import render_summary_cards
from utils.dates import get_week_dates, format_date
from utils.export import export_to_excel

# 可作为固定班次指定的类型
_FIXED_TYPES = [AssignmentType.EARLY, AssignmentType.MID, AssignmentType.LATE,
                AssignmentType.OFFICE, AssignmentType.EXTERNAL]
_FIXED_LABELS = [ASSIGNMENT_LABELS[t] for t in _FIXED_TYPES]
_LABEL_TO_TYPE = {ASSIGNMENT_LABELS[t]: t for t in _FIXED_TYPES}


def _clear_result():
    for k in ["current_solution", "current_score", "current_status",
              "current_params", "sel_names", "sel_ids",
              "schedule_saved", "last_saved_week"]:
        st.session_state.pop(k, None)


def main():
    apply_styles()
    page_header("排班生成", "每周自动排班 · 支持历史均衡、坐班配额与外派轮换")

    init_db()
    session = get_session()
    seed_staff(session)
    active_staff = get_active_staff(session)

    if not active_staff:
        note("花名册暂无在职人员，请先到「人员花名册」添加。")
        session.close()
        return

    # ── 1. 排班周期与班次模式 ───────────────────────────
    section_title("排班周期", "选择周一为起始日")
    c1, c2, c3 = st.columns([1.1, 1, 1.4])
    with c1:
        monday = date.today() - timedelta(days=date.today().weekday())
        picked = st.date_input("排班周（周一）", value=monday)
        week_start = picked - timedelta(days=picked.weekday())
    with c2:
        shift_model = st.radio("班次模式", [3, 4], index=0, horizontal=True,
                               format_func=lambda x: f"{x} 班",
                               help="3 班：早/中/晚；4 班：早/白/午/晚")
    with c3:
        week_dates = get_week_dates(week_start)
        st.markdown(
            f'<div style="padding-top:1.9rem;" class="tip">周期：'
            f'{format_date(week_dates[0])} — {format_date(week_dates[-1])}</div>',
            unsafe_allow_html=True,
        )

    # ── 2. 在岗人员与配额（表格编辑，替代一堆勾选框） ──────
    section_title("在岗与配额", "勾选本周在岗人员，直接在表中调整工作天数与坐班")

    # 自动标记最近外派过的人（默认不可再排外派）
    ext_history = get_external_history(session)
    recent_ext_ids = set()
    if ext_history:
        latest = ext_history[0]["week_start"]
        recent_ext_ids = {h["staff_id"] for h in ext_history if h["week_start"] == latest}

    name_to_id = {s.name: s.id for s in active_staff}
    # 智能计算默认坐班：总工作天 - 跟播 = 所需坐班，均匀分配
    default_work = 5
    total_work_est = len(active_staff) * default_work
    shift_slots_est = shift_model * 7
    office_needed_est = max(0, total_work_est - shift_slots_est)
    base_office = office_needed_est // len(active_staff) if active_staff else 0
    extra_office = office_needed_est % len(active_staff)

    base_rows = []
    for i, s in enumerate(active_staff):
        office_days = base_office + (1 if i < extra_office else 0)
        base_rows.append({
            "在岗": True,
            "姓名": s.name,
            "工作天数": default_work,
            "坐班": office_days,
            "可外派": s.id not in recent_ext_ids,
        })

    roster = st.data_editor(
        pd.DataFrame(base_rows),
        hide_index=True,
        use_container_width=True,
        column_config={
            "在岗": st.column_config.CheckboxColumn("在岗", width="small"),
            "姓名": st.column_config.TextColumn("姓名", disabled=True, width="medium"),
            "工作天数": st.column_config.NumberColumn("工作天数", min_value=0, max_value=7,
                                                  step=1, width="small"),
            "坐班": st.column_config.NumberColumn("坐班天数", min_value=0, max_value=7,
                                                step=1, width="small"),
            "可外派": st.column_config.CheckboxColumn("可外派", width="small",
                                                  help="最近排过外派的人默认取消勾选"),
        },
        key="roster_editor",
    )

    on_duty = roster[roster["在岗"]].reset_index(drop=True)
    selected_names = on_duty["姓名"].tolist()
    selected_ids = [name_to_id[n] for n in selected_names]
    n = len(selected_names)

    rest_days_input = {i: 7 - int(on_duty.loc[i, "工作天数"]) for i in range(n)}
    office_quota_input = {i: int(on_duty.loc[i, "坐班"]) for i in range(n)}
    external_exclude_set = {i for i in range(n) if not bool(on_duty.loc[i, "可外派"])}
    name_to_pidx = {name: i for i, name in enumerate(selected_names)}

    office_total = sum(office_quota_input.values())
    total_work_days = sum(int(on_duty.loc[i, "工作天数"]) for i in range(n))
    shift_slots = shift_model * 7
    # 数学公式: 总工作天 = 跟播班次 + 坐班 + 外派
    # 所以 坐班 = 总工作天 - 跟播班次 - 外派
    needed_office_no_ext = total_work_days - shift_slots  # 不含外派的坐班需求

    kpi_row([
        ("在岗人数", n, "good" if n >= shift_model else "bad",
         f"班次模式需 ≥ {shift_model} 人"),
        ("坐班合计", f"{office_total} 天",
         "good" if office_total <= needed_office_no_ext else "warn"),
        ("可外派人数", n - len(external_exclude_set), ""),
    ])

    if n == 0:
        note("请至少勾选 1 名在岗人员。")
        session.close()
        return

    if office_total > needed_office_no_ext:
        st.warning(
            f"⚠️ 坐班合计 {office_total} 天超出了上限 {needed_office_no_ext} 天"
            f"（{n}人共 {total_work_days} 工作天 - {shift_model}班×7天={shift_slots}）。"
            f"请减少「坐班天数」。",
            icon="⚠️"
        )
    elif office_total < needed_office_no_ext and n > 0:
        shortage = needed_office_no_ext - office_total
        st.warning(
            f"⚠️ 坐班合计仅 {office_total} 天，还差 **{shortage}** 天才能配平"
            f"（{n}人共 {total_work_days} 工作天 - {shift_model}班×7天={shift_slots}={needed_office_no_ext}）。"
            f"请在上方表格中增加「坐班天数」列。",
            icon="⚠️"
        )

    # ── 3. 高级选项（默认折叠，保持主界面清爽） ───────────
    section_title("高级选项", "外派、固定班次、强制休息等微调")
    external_total = 0
    max_consecutive = 5
    fixed_assignments = []

    with st.expander("外派与连续工作上限", expanded=False):
        ec1, ec2 = st.columns(2)
        with ec1:
            external_total = st.number_input("外派总天数", min_value=0, max_value=7, value=0,
                                             help="本周需要外派支援的总人天数")
        with ec2:
            max_consecutive = st.number_input("最大连续工作天数", min_value=3, max_value=7,
                                              value=5)
        if recent_ext_ids:
            st.markdown('<div class="tip">已根据历史自动取消最近外派人员的「可外派」勾选。</div>',
                        unsafe_allow_html=True)

    with st.expander("固定班次（某人某天指定班次）", expanded=False):
        fixed_df = st.data_editor(
            pd.DataFrame({"人员": pd.Series(dtype="str"),
                          "星期": pd.Series(dtype="str"),
                          "班次": pd.Series(dtype="str")}),
            num_rows="dynamic", hide_index=True, use_container_width=True,
            column_config={
                "人员": st.column_config.SelectboxColumn("人员", options=selected_names),
                "星期": st.column_config.SelectboxColumn("星期", options=DAY_NAMES),
                "班次": st.column_config.SelectboxColumn("班次", options=_FIXED_LABELS),
            },
            key="fixed_editor",
        )
        for _, r in fixed_df.iterrows():
            if r["人员"] in name_to_pidx and r["星期"] in DAY_NAMES and r["班次"] in _LABEL_TO_TYPE:
                fixed_assignments.append(
                    (name_to_pidx[r["人员"]], DAY_NAMES.index(r["星期"]), _LABEL_TO_TYPE[r["班次"]])
                )

    with st.expander("强制休息（某人某天必须休息）", expanded=False):
        rest_df = st.data_editor(
            pd.DataFrame({"人员": pd.Series(dtype="str"), "星期": pd.Series(dtype="str")}),
            num_rows="dynamic", hide_index=True, use_container_width=True,
            column_config={
                "人员": st.column_config.SelectboxColumn("人员", options=selected_names),
                "星期": st.column_config.SelectboxColumn("星期", options=DAY_NAMES),
            },
            key="rest_editor",
        )
        for _, r in rest_df.iterrows():
            if r["人员"] in name_to_pidx and r["星期"] in DAY_NAMES:
                fixed_assignments.append(
                    (name_to_pidx[r["人员"]], DAY_NAMES.index(r["星期"]), AssignmentType.REST)
                )

    # ── 4. 操作按钮 ─────────────────────────────────
    divider()
    c_gen, c_confirm = st.columns([1, 1])
    with c_gen:
        gen = st.button("🔄 生成排班", type="primary", use_container_width=True)
    with c_confirm:
        has_result = "current_solution" in st.session_state
        already_saved = st.session_state.get("schedule_saved", False)
        if already_saved:
            st.button("✅ 已记录", disabled=True, use_container_width=True,
                      help="当前排班已存入历史记录，重新生成后可再次记录")
            confirm = False
        else:
            confirm = st.button("📝 确认并记录", type="secondary",
                               use_container_width=True, disabled=not has_result,
                               help="确认排班无误后存入历史记录，避免反复调整时产生冗余记录")

    # 上周排班（折叠预览，便于参考接续）
    prev = get_prev_schedule(session, week_start)
    if prev and prev.entries:
        with st.expander("查看上周排班", expanded=False):
            staff_map = {s.id: s.name for s in active_staff}
            render_entries_grid(prev.entries, staff_map,
                                week_dates=get_week_dates(prev.week_start))

    # ── 5. 求解 ─────────────────────────────────────
    if gen:
        # ── 自动配平坐班（公式: 坐班 = 总工作天 - 跟播 - 外派）──
        total_work = sum(7 - rest_days_input[i] for i in range(n))
        shift_slots_final = shift_model * 7
        ext_sum = int(external_total)
        target_office = total_work - shift_slots_final - ext_sum

        office_quota_input = dict(office_quota_input)  # copy
        current_office = sum(office_quota_input.values())
        gap = target_office - current_office

        if target_office < 0:
            st.error(
                f"❌ 人手不足：{n}人共 {total_work} 工作天，但 "
                f"{shift_model}班×7天={shift_slots_final}跟播 + {ext_sum}外派 = {shift_slots_final + ext_sum}，"
                f"差 {abs(target_office)} 天。请增加「工作天数」或减少「外派」。"
            )
            session.close()
            return

        if gap != 0:
            # 从工作天数>0的人中加减坐班，每人每天最多±1，且坐班不超过工作天数
            candidates = [i for i in range(n) if rest_days_input[i] < 7]
            max_office = {i: 7 - rest_days_input[i] for i in range(n)}  # 每人最大坐班 = 工作天数
            if gap > 0:
                for _ in range(gap):
                    # 找坐班最少且还有余量的人
                    i = min(candidates, key=lambda x: (office_quota_input.get(x, 0),
                                                        -max_office.get(x, 0)))
                    if office_quota_input.get(i, 0) < max_office[i]:
                        office_quota_input[i] = office_quota_input.get(i, 0) + 1
            else:
                for _ in range(-gap):
                    i = max(candidates, key=lambda x: office_quota_input.get(x, 0))
                    if office_quota_input.get(i, 0) > 0:
                        office_quota_input[i] -= 1

            st.info(
                f"💡 坐班已自动配平：{current_office} → {target_office} 天 "
                f"（总工作{total_work} - {shift_model}班×7天={shift_slots_final}跟播 - {ext_sum}外派 = {target_office}）",
                icon="💡"
            )

        staff_id_list = list(zip(selected_ids, selected_names))
        prev_counts = compute_balance_targets(session, staff_id_list, week_start)
        params = {
            "rest_days": rest_days_input,
            "office_quota": office_quota_input,
            "external_total": int(external_total),
            "external_exclude": external_exclude_set,
            "fixed_assignments": fixed_assignments,
            "max_consecutive_work": int(max_consecutive),
            "prev_shift_counts": prev_counts,
            "priority_rest": [],
            "priority_rest_weight": 50,
        }
        with st.spinner("正在求解，请稍候…"):
            status, solution, score = build_and_solve(n, params, timeout=60)

        if status == "INFEASIBLE" or solution is None:
            st.error("无法生成可行排班，参数可能存在矛盾。")
            note("常见原因：坐班配额之和与人手不匹配 · 固定班次与强制休息冲突 · "
                 "外派排除后无人可排外派 · 工作天数过低导致班次无法覆盖。")
            # 可复制的参数文本框
            import json as _json
            debug_params = {
                "n": n, "selected_names": selected_names,
                "rest_days": {str(k): v for k, v in rest_days_input.items()},
                "office_quota": {str(k): v for k, v in office_quota_input.items()},
                "external_total": int(external_total),
                "external_exclude": list(external_exclude_set),
                "fixed_assignments": [(int(p), int(d), int(t)) for (p, d, t) in fixed_assignments],
                "max_consecutive_work": int(max_consecutive),
                "total_work": total_work,
                "shift_slots": shift_slots_final,
                "target_office": target_office,
            }
            st.code(_json.dumps(debug_params, ensure_ascii=False, indent=2), language="json")
            session.close()
            return

        st.session_state.update({
            "current_solution": solution, "current_score": score,
            "current_status": status, "current_params": params,
            "sel_names": selected_names, "sel_ids": selected_ids,
            "schedule_saved": False,
        })

    if "current_solution" not in st.session_state:
        session.close()
        return

    # ── 6. 结果展示 ─────────────────────────────────
    solution = st.session_state["current_solution"]
    score = st.session_state.get("current_score", 0)
    status = st.session_state.get("current_status", "?")
    params = st.session_state.get("current_params", {})
    names = st.session_state.get("sel_names", selected_names)
    ids = st.session_state.get("sel_ids", selected_ids)

    section_title("排班结果", f"{format_date(week_dates[0])} — {format_date(week_dates[-1])}")
    status_cn = {"OPTIMAL": "最优解", "FEASIBLE": "可行解"}.get(status, status)
    kpi_row([
        ("求解状态", status_cn, "good" if status == "OPTIMAL" else "warn"),
        ("目标值", score if score is not None else "—", ""),
        ("在岗人数", len(names), ""),
    ])

    # 显示格式切换（用 container 稳定包裹，避免切换时 DOM 冲突）
    if "view_mode" not in st.session_state:
        st.session_state.view_mode = "传统班表（行=班次，列=日期）"
    view_mode = st.radio("显示格式", ["人员矩阵（行=人，列=日期）",
                                       "传统班表（行=班次，列=日期）"],
                          horizontal=True, index=1, key="view_mode_radio",
                          on_change=lambda: st.session_state.update(
                              view_mode=st.session_state.view_mode_radio))
    st.session_state.view_mode = view_mode

    # 手动微调 toggle 始终渲染（避免条件创建/销毁）
    manual = st.toggle("手动微调模式", value=False,
                       help="开启后可直接编辑矩阵，修改后重新校验约束",
                       key="manual_toggle",
                       disabled=view_mode.startswith("传统"))

    if view_mode.startswith("传统"):
        with st.container(key="trad_view_container"):
            render_traditional_grid(solution, names, week_dates=week_dates)
            trad_text = build_traditional_text(solution, names, week_dates=week_dates)
            with st.expander("📋 复制纯文本（粘贴到在线表格）", expanded=False):
                # 强制刷新 text_area 值，避免 Streamlit key 缓存旧内容
                st.session_state["trad_textarea"] = trad_text
                st.text_area("排班表", height=200, key="trad_textarea",
                             label_visibility="collapsed")
        current = solution
    else:
        with st.container(key="matrix_view_container"):
            if manual:
                current = render_schedule_editor(solution, names, key_prefix="manual")
                st.markdown('<div class="tip">修改后点击下方「重新校验」更新结果。</div>',
                            unsafe_allow_html=True)
            else:
                render_readonly_grid(solution, names, week_dates=week_dates)
                current = solution

    section_title("工时对账")
    render_summary_cards(current, names)

    section_title("约束校验")
    violations = validate_schedule(current, len(ids), 7, SHIFT_TYPES, params)
    if violations:
        st.markdown(
            f'<div class="vbar fail"><span class="ico">✕</span>'
            f'发现 {len(violations)} 处约束未满足</div>', unsafe_allow_html=True)
        st.markdown('<ul class="vlist">' + "".join(f"<li>{v}</li>" for v in violations) +
                    '</ul>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="vbar pass"><span class="ico">✓</span>'
                    '所有硬约束均已满足</div>', unsafe_allow_html=True)

    # ── 确认记录（处理顶部按钮点击）──────────────────
    if confirm:
        entries_data = [{
            "staff_id": ids[p], "day_of_week": d,
            "assignment_type": int(t), "remark": None,
        } for (p, d), t in current.items()]
        config_dict = {
            "rest_days": {str(k): v for k, v in params.get("rest_days", {}).items()},
            "office_quota": {str(k): v for k, v in params.get("office_quota", {}).items()},
            "external_total": params.get("external_total", 0),
        }
        save_schedule(session, week_start, entries_data, shift_model=shift_model,
                      config_json=json.dumps(config_dict, ensure_ascii=False),
                      solver_score=score)
        st.session_state["schedule_saved"] = True
        st.success(f"✅ 已确认并记录（{week_start} 周），可在「历史记录」中查看")
        st.rerun()

    divider()
    b1, b2, b3, b4 = st.columns(4)
    with b1:
        if st.button("保存排班", type="primary", use_container_width=True):
            entries_data = [{
                "staff_id": ids[p], "day_of_week": d,
                "assignment_type": int(t), "remark": None,
            } for (p, d), t in current.items()]
            config_dict = {
                "rest_days": {str(k): v for k, v in params.get("rest_days", {}).items()},
                "office_quota": {str(k): v for k, v in params.get("office_quota", {}).items()},
                "external_total": params.get("external_total", 0),
            }
            save_schedule(session, week_start, entries_data, shift_model=shift_model,
                          config_json=json.dumps(config_dict, ensure_ascii=False),
                          solver_score=score)
            st.session_state["schedule_saved"] = True
            st.success(f"已保存（{week_start} 周）")
    with b2:
        st.download_button(
            "导出 Excel",
            data=export_to_excel(current, names, week_start),
            file_name=f"排班_{week_start}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with b3:
        if st.button("重新生成", use_container_width=True):
            _clear_result()
            st.rerun()
    with b4:
        if manual and st.button("重新校验", use_container_width=True):
            st.session_state["current_solution"] = current
            st.session_state["schedule_saved"] = False
            st.rerun()

    session.close()


main()

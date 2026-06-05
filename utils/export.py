"""Excel/CSV 导出工具。"""

import io
import pandas as pd
from datetime import date
from config import DAY_NAMES, ASSIGNMENT_LABELS


def schedule_to_dataframe(solution, staff_names, num_days=7):
    """将排班结果转为 DataFrame。

    Args:
        solution: dict {(p, d): AssignmentType}
        staff_names: list of str
        num_days: 天数

    Returns:
        pd.DataFrame: 行=人员, 列=周几
    """
    data = {}
    for p, name in enumerate(staff_names):
        row = []
        for d in range(num_days):
            t = solution.get((p, d))
            row.append(ASSIGNMENT_LABELS.get(t, '?'))
        data[name] = row

    df = pd.DataFrame(data).T
    df.columns = DAY_NAMES[:num_days]
    return df


def export_to_excel(solution, staff_names, week_start, num_days=7):
    """导出为 Excel 二进制数据。"""
    df = schedule_to_dataframe(solution, staff_names, num_days)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=f'排班_{week_start}')
        # 调整列宽
        ws = writer.sheets[f'排班_{week_start}']
        ws.column_dimensions['A'].width = 12
        for i in range(num_days):
            col_letter = chr(ord('B') + i)
            ws.column_dimensions[col_letter].width = 14

    return output.getvalue()

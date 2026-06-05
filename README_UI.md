# UI 维护说明

本次重做只改动了 **UI 层**。求解器 `solver/`、数据库 `database/`、`config.py` 的逻辑保持原样。

## 改样式去哪

所有视觉集中在 **`ui/styles.py`**：

- 配色：改 `:root` 里的 CSS 变量（以及顶部 `COLORS` 字典，供 Python 侧引用），全站颜色统一跟着变。
- 字体：`--font` 变量，目前是纯系统字体栈，未引用任何外部 CDN。
- 班次底色：`.cell-*` 与 `.badge-*` 两组 class。
- 间距/圆角/阴影：`--r-*`、`--shadow`、`.block-container` 的 padding。

页面里不要写零散的内联样式，统一用 `styles.py` 提供的辅助函数：
`page_header()`、`section_title()`、`kpi_row()`、`note()`、`divider()`。

## 文件职责

| 文件 | 作用 |
|---|---|
| `app.py` | 入口、页面配置、侧边栏导航 |
| `ui/styles.py` | 设计系统 + 版式辅助函数（**改样式只看这里**） |
| `ui/components/schedule_grid.py` | 排班矩阵：只读彩色表 / 可编辑器 / 从 DB 还原 |
| `ui/components/summary_cards.py` | 每人工时对账卡片 |
| `ui/pages/generator.py` | 排班生成（周期→在岗配额表→高级折叠→生成→结果） |
| `ui/pages/history.py` | 历史浏览 + 累计分布 |
| `ui/pages/staff_mgmt.py` | 人员花名册增删改 |
| `ui/preview.html` | 离线视觉预览，浏览器直接打开即可看效果 |

## 主要交互变化

- 原来挤在侧边栏的几十个控件，改到主区域：在岗人员/工作天数/坐班/可外派合并成 **一张可编辑表格**；外派、固定班次、强制休息收进 **折叠面板**；侧边栏只留导航。
- 排班矩阵表头显示「周几 + 日期」，姓名列固定，长表横向滚动不丢列名。
- 历史页用周次下拉 + 概览指标 + 彩色矩阵 + 累计分布（带进度条）。

## 运行

```bash
pip install -r requirements.txt
streamlit run app.py
```

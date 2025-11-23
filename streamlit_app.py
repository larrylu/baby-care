import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta, timezone

# --- 1. 核心配置：定义北京时间 (东八区) ---
# 无论服务器在哪，都强制使用这个时区
BJ_TZ = timezone(timedelta(hours=8), 'Beijing')

DATA_FILE = 'family_data.json'

# --- 预设的待办事项模版 ---
TEMPLATE_TASKS = [
    # === 👶 宝宝任务 ===
    {"id": 1, "category": "baby", "task": "【疫苗】乙肝疫苗第一针", "offset_hours": 24, "desc": "出生24小时内接种"},
    {"id": 2, "category": "baby", "task": "【疫苗】卡介苗", "offset_hours": 24, "desc": "出生24小时内接种"},
    {"id": 3, "category": "baby", "task": "【筛查】听力筛查", "offset_hours": 72, "desc": "出生72小时左右进行"},
    {"id": 4, "category": "baby", "task": "【筛查】足跟血采集", "offset_hours": 72, "desc": "出生72小时后，7天之内"},
    {"id": 5, "category": "baby", "task": "【护理】脐带脱落观察", "offset_hours": 168, "desc": "通常7-14天，保持干燥"},
    {"id": 6, "category": "baby", "task": "【检查】黄疸复测", "offset_hours": 168, "desc": "出院后一周复查皮测黄疸值"},
    {"id": 7, "category": "baby", "task": "【疫苗】乙肝疫苗第二针", "offset_hours": 720, "desc": "满月（30天）接种"},
    {"id": 8, "category": "baby", "task": "【体检】满月体检", "offset_hours": 720, "desc": "测身高体重头围，评估生长发育"},
    {"id": 9, "category": "baby", "task": "【补充】补充维生素D3", "offset_hours": 360, "desc": "出生15天后开始每天补充400IU"},
    
    # === 👩 妈妈任务 ===
    {"id": 101, "category": "mom", "task": "【产后】首次排尿", "offset_hours": 6, "desc": "顺产/拔尿管后4-6小时内必须排尿"},
    {"id": 102, "category": "mom", "task": "【产后】下床活动", "offset_hours": 24, "desc": "顺产6-12小时，剖腹产24小时后"},
    {"id": 103, "category": "mom", "task": "【护理】会阴/伤口消毒", "offset_hours": 24, "desc": "每日2次，保持清洁干燥"},
    {"id": 104, "category": "mom", "task": "【乳房】生理性涨奶冷敷", "offset_hours": 72, "desc": "产后3-4天出现，冷敷缓解"},
    {"id": 105, "category": "mom", "task": "【检查】产后42天检查", "offset_hours": 1008, "desc": "盆底肌、腹直肌、子宫复旧情况检查"},
]

# --- 辅助工具：秒级时间格式化 ---
def format_timedelta(td):
    """将 timedelta 转换为 D天 H时 M分 S秒"""
    total_seconds = int(td.total_seconds())
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{days}天 {hours}小时 {minutes}分 {seconds}秒"

def get_current_bj_time():
    """获取当前的北京时间"""
    return datetime.now(BJ_TZ)

# --- 数据读写 ---
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"birth_time": None, "tasks": {}}
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- 页面配置 ---
st.set_page_config(page_title="家庭新生儿管家", page_icon="🏠", layout="centered")

# --- 组件：渲染单个任务卡片 ---
def render_task_card(task_item, current_time, data, tab_key_prefix):
    task_meta = task_item["meta"]
    due_time = task_item["due_time"]
    is_overdue = task_item["is_overdue"]
    status_str = task_item["status_str"]
    task_id = str(task_meta["id"])

    with st.container():
        icon = "👶" if task_meta["category"] == "baby" else "👩"
        
        # 样式逻辑
        if is_overdue:
            st.error(f"{icon} **{task_meta['task']}**")
            st.caption(f"🔴 {status_str}")
        else:
            time_left = due_time - current_time
            # 小于12小时显示橙色
            if time_left.total_seconds() < 12 * 3600:
                 st.warning(f"{icon} **{task_meta['task']}**")
                 st.caption(f"🟠 {status_str}")
            else:
                st.info(f"{icon} **{task_meta['task']}**")
                st.caption(f"🟢 {status_str}")
        
        col1, col2 = st.columns([3, 1.2])
        with col1:
            st.text(f"说明: {task_meta['desc']}")
            # 这里的截止时间也显示到秒，明确时间点
            st.text(f"截止: {due_time.strftime('%m-%d %H:%M:%S')}")
            note_key = f"note_{tab_key_prefix}_{task_id}"
            note = st.text_input("备注", key=note_key, placeholder="记录数值或情况...")
            
        with col2:
            st.write("")
            st.write("")
            btn_key = f"btn_{tab_key_prefix}_{task_id}"
            if st.button("✅ 完成", key=btn_key, use_container_width=True):
                data["tasks"][task_id] = {
                    "status": "done",
                    "done_at": current_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "note": note
                }
                save_data(data)
                st.toast(f"{task_meta['task']} 完成！")
                st.rerun()
        st.divider()

# --- 核心：秒级自动刷新仪表盘 ---
# run_every=1 代表每秒刷新一次，实现秒表跳动效果
@st.fragment(run_every=1)
def render_live_dashboard():
    data = load_data()
    
    if not data["birth_time"]:
        return False # 没数据，交给主函数显示初始化界面

    # 1. 统一时间基准：所有字符串转回北京时间对象
    birth_time_str = data["birth_time"]
    # 解析字符串，并强制指定为北京时间
    birth_time = datetime.strptime(birth_time_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=BJ_TZ)
    now = get_current_bj_time()
    
    # 2. 实时年龄 (精确到秒)
    age_delta = now - birth_time
    st.success(f"📅 宝宝已出生: **{format_timedelta(age_delta)}**\n\n(北京时间: {now.strftime('%H:%M:%S')})")

    # 3. 任务计算
    pending_tasks_all = []
    
    for task in TEMPLATE_TASKS:
        task_id = str(task["id"])
        record = data["tasks"].get(task_id)
        if record and record["status"] == "done":
            continue 
            
        due_time = birth_time + timedelta(hours=task["offset_hours"])
        is_overdue = now > due_time
        time_diff = due_time - now if not is_overdue else now - due_time
        
        # 格式化时间字符串
        time_str = format_timedelta(time_diff)
        
        if is_overdue:
            status_str = f"已超期 {time_str}"
        else:
            status_str = f"剩余 {time_str}"
            
        pending_tasks_all.append({
            "meta": task,
            "due_time": due_time,
            "is_overdue": is_overdue,
            "status_str": status_str
        })

    pending_tasks_all.sort(key=lambda x: x["due_time"])
    pending_baby = [t for t in pending_tasks_all if t["meta"]["category"] == "baby"]
    pending_mom = [t for t in pending_tasks_all if t["meta"]["category"] == "mom"]

    # 4. Tabs 界面
    tab_home, tab_baby, tab_mom, tab_history, tab_settings = st.tabs(["🏠 总览", "👶 宝宝", "👩 妈妈", "📜 记录", "⚙️ 设置"])

    with tab_home:
        if not pending_tasks_all:
            st.info("🎉 无待办事项")
        else:
            for item in pending_tasks_all:
                render_task_card(item, now, data, "home")

    with tab_baby:
        if not pending_baby: st.info("宝宝任务完成")
        else:
            for item in pending_baby: render_task_card(item, now, data, "baby")

    with tab_mom:
        if not pending_mom: st.info("妈妈任务完成")
        else:
            for item in pending_mom: render_task_card(item, now, data, "mom")

    with tab_history:
        # 添加手动刷新按钮，因为 fragment 可能会缓存表格状态
        if st.button("🔄 刷新表格"): pass

        completed_list = []
        for t_id, record in data["tasks"].items():
            if record["status"] == "done":
                orig_task = next((t for t in TEMPLATE_TASKS if str(t["id"]) == t_id), None)
                if orig_task:
                    completed_list.append({
                        "对象": orig_task["category"],
                        "任务": orig_task["task"],
                        "完成时间": record["done_at"], # 这里已经是秒级字符串了
                        "备注": record.get("note", "")
                    })
        if completed_list:
            df = pd.DataFrame(completed_list).sort_values("完成时间", ascending=False)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.caption("暂无记录")

    # --- 3. 清空数据二次确认逻辑 (在设置 Tab 中) ---
    with tab_settings:
        st.write("### 数据管理")
        st.info(f"当前出生时间设定: {birth_time_str}")
        
        # 使用 session_state 管理确认状态
        if 'confirm_delete_step' not in st.session_state:
            st.session_state['confirm_delete_step'] = False

        if not st.session_state['confirm_delete_step']:
            # 第一步：点击清空按钮
            if st.button("🗑️ 清空所有数据"):
                st.session_state['confirm_delete_step'] = True
                st.rerun() # 重新运行以显示警告
        else:
            # 第二步：显示警告和确认/取消
            st.warning("⚠️ 警告：此操作将永久删除所有出生信息和打卡记录，不可恢复！")
            col_yes, col_no = st.columns(2)
            with col_yes:
                if st.button("✅ 确认删除", type="primary"):
                    if os.path.exists(DATA_FILE):
                        os.remove(DATA_FILE)
                    # 重置状态
                    st.session_state['confirm_delete_step'] = False
                    st.success("数据已清空，正在重置...")
                    st.rerun()
            with col_no:
                if st.button("❌ 取消"):
                    st.session_state['confirm_delete_step'] = False
                    st.rerun()

    return True

# --- 主程序入口 ---
def main():
    st.title("🏠 新生儿家庭任务管家")
    
    data = load_data()
    
    if not data["birth_time"]:
        st.warning("👋 请先设置宝宝出生时间")
        
        # 获取当前北京时间作为默认值
        now_bj = get_current_bj_time()
        
        col1, col2 = st.columns(2)
        d = col1.date_input("出生日期", value=now_bj)
        t = col2.time_input("出生时间", value=now_bj) # 默认显示当前北京时间
        
        if st.button("🚀 启动 (以北京时间记录)"):
            # 组合日期和时间，并附加时区信息
            birth_dt = datetime.combine(d, t).replace(tzinfo=BJ_TZ)
            data["birth_time"] = birth_dt.strftime("%Y-%m-%d %H:%M:%S")
            save_data(data)
            st.rerun()
    else:
        render_live_dashboard()

if __name__ == "__main__":
    main()

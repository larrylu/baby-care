import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta

# --- 配置文件路径 ---
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

# --- 渲染单个卡片 ---
def render_task_card(task_item, current_time, data, tab_key_prefix):
    task_meta = task_item["meta"]
    due_time = task_item["due_time"]
    is_overdue = task_item["is_overdue"]
    status_str = task_item["status_str"]
    task_id = str(task_meta["id"])

    with st.container():
        # 标题栏
        icon = "👶" if task_meta["category"] == "baby" else "👩"
        
        # 动态计算剩余时间颜色
        if is_overdue:
            st.error(f"{icon} **{task_meta['task']}**")
            st.caption(f"🔴 {status_str}")
        else:
            # 如果剩余时间小于12小时，用橙色提醒，否则蓝色
            time_left = due_time - current_time
            if time_left.total_seconds() < 12 * 3600:
                 st.warning(f"{icon} **{task_meta['task']}**")
                 st.caption(f"🟠 {status_str}")
            else:
                st.info(f"{icon} **{task_meta['task']}**")
                st.caption(f"🟢 {status_str}")
        
        col1, col2 = st.columns([3, 1.2])
        with col1:
            st.text(f"说明: {task_meta['desc']}")
            st.text(f"截止: {due_time.strftime('%m-%d %H:%M')}")
            # 备注框
            note_key = f"note_{tab_key_prefix}_{task_id}"
            note = st.text_input("备注", key=note_key, placeholder="情况记录...")
            
        with col2:
            st.write("")
            st.write("")
            # 完成按钮
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

# --- 核心动态渲染区 (关键修改点) ---
# run_every=60 表示每60秒自动刷新这个函数内部的内容
@st.fragment(run_every=60)
def render_live_dashboard():
    data = load_data()
    
    # 如果没设置时间，不显示仪表盘，返回False让主程序处理
    if not data["birth_time"]:
        return False

    birth_time = datetime.strptime(data["birth_time"], "%Y-%m-%d %H:%M:%S")
    now = datetime.now()
    
    # 1. 实时更新的宝宝年龄
    age_delta = now - birth_time
    st.success(f"📅 宝宝已出生: **{age_delta.days}天 {age_delta.seconds//3600}小时** (当前时间: {now.strftime('%H:%M')})")

    # 2. 实时计算任务状态
    pending_tasks_all = []
    
    for task in TEMPLATE_TASKS:
        task_id = str(task["id"])
        record = data["tasks"].get(task_id)
        if record and record["status"] == "done":
            continue 
            
        due_time = birth_time + timedelta(hours=task["offset_hours"])
        is_overdue = now > due_time
        time_diff = due_time - now
        
        if is_overdue:
            status_str = f"已超期 {abs(time_diff.days)}天 {abs(time_diff.seconds)//3600}小时 {abs(time_diff.seconds)%3600//60}分"
        else:
            status_str = f"剩余 {time_diff.days}天 {time_diff.seconds//3600}小时 {time_diff.seconds%3600//60}分"
            
        pending_tasks_all.append({
            "meta": task,
            "due_time": due_time,
            "is_overdue": is_overdue,
            "status_str": status_str
        })

    pending_tasks_all.sort(key=lambda x: x["due_time"])
    pending_baby = [t for t in pending_tasks_all if t["meta"]["category"] == "baby"]
    pending_mom = [t for t in pending_tasks_all if t["meta"]["category"] == "mom"]

    # 3. Tabs 展示
    tab_home, tab_baby, tab_mom, tab_history = st.tabs(["🏠 待办总览", "👶 宝宝待办", "👩 妈妈待办", "📜 历史记录"])

    with tab_home:
        if not pending_tasks_all:
            st.info("🎉 目前没有任何待办事项！")
        else:
            for item in pending_tasks_all:
                render_task_card(item, now, data, "home")

    with tab_baby:
        if not pending_baby:
            st.info("宝宝任务已全部完成")
        else:
            for item in pending_baby:
                render_task_card(item, now, data, "baby")

    with tab_mom:
        if not pending_mom:
            st.info("妈妈任务已全部完成")
        else:
            for item in pending_mom:
                render_task_card(item, now, data, "mom")

    with tab_history:
        # 历史记录不需要实时刷新，但为了放在Tab里，只能写在这里
        # 或者可以将历史记录移出 fragment，但那样布局会断裂
        if st.button("🔄 刷新历史记录"):
            pass # 按钮本身会触发刷新
            
        completed_list = []
        for t_id, record in data["tasks"].items():
            if record["status"] == "done":
                orig_task = next((t for t in TEMPLATE_TASKS if str(t["id"]) == t_id), None)
                if orig_task:
                    completed_list.append({
                        "对象": orig_task["category"],
                        "任务": orig_task["task"],
                        "完成时间": record["done_at"][5:-3],
                        "备注": record.get("note", "")
                    })
        if completed_list:
            df = pd.DataFrame(completed_list).sort_values("完成时间", ascending=False)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.caption("暂无记录")
    
    return True

# --- 主入口 ---
def main():
    st.title("🏠 新生儿家庭任务管家")
    
    # 尝试加载数据判断是否需要显示“初始化界面”
    data = load_data()
    
    if not data["birth_time"]:
        st.warning("👋 请先设置宝宝出生时间")
        col1, col2 = st.columns(2)
        d = col1.date_input("出生日期", value=datetime.now())
        t = col2.time_input("出生时间", value=datetime.now())
        if st.button("🚀 启动"):
            birth_dt = datetime.combine(d, t)
            data["birth_time"] = birth_dt.strftime("%Y-%m-%d %H:%M:%S")
            save_data(data)
            st.rerun()
    else:
        # 调用自动刷新的片段
        render_live_dashboard()

if __name__ == "__main__":
    main()

import streamlit as st
import pandas as pd
import json
import os
import time
import uuid
from datetime import datetime, timedelta, timezone

# --- 尝试导入历法库 ---
try:
    from lunar_python import Solar
    HAS_LUNAR_LIB = True
except ImportError:
    HAS_LUNAR_LIB = False

# --- 1. 基础配置 & 常量 ---
BJ_TZ = timezone(timedelta(hours=8), 'Beijing')
USERS_FILE = 'app_users.json'

# 系统预设模版
DEFAULT_TEMPLATE = [
    {"id": "sys_1", "category": "baby", "task": "【疫苗】乙肝疫苗第一针", "offset_seconds": 24*3600, "desc": "出生24h内"},
    {"id": "sys_2", "category": "baby", "task": "【疫苗】卡介苗", "offset_seconds": 24*3600, "desc": "出生24h内"},
    {"id": "sys_3", "category": "baby", "task": "【筛查】听力筛查", "offset_seconds": 72*3600, "desc": "出生72h左右"},
    {"id": "sys_4", "category": "baby", "task": "【筛查】足跟血采集", "offset_seconds": 72*3600, "desc": "出生72h后"},
    {"id": "sys_5", "category": "baby", "task": "【护理】脐带脱落观察", "offset_seconds": 7*24*3600, "desc": "7-14天"},
    {"id": "sys_6", "category": "baby", "task": "【检查】黄疸复测", "offset_seconds": 7*24*3600, "desc": "出院一周后"},
    {"id": "sys_7", "category": "baby", "task": "【疫苗】乙肝疫苗第二针", "offset_seconds": 30*24*3600, "desc": "满月接种"},
    {"id": "sys_8", "category": "baby", "task": "【体检】满月体检", "offset_seconds": 30*24*3600, "desc": "身长体重头围"},
    {"id": "sys_9", "category": "baby", "task": "【补充】补充维生素D3", "offset_seconds": 15*24*3600, "desc": "出生15天后"},
    {"id": "sys_101", "category": "mom", "task": "【产后】首次排尿", "offset_seconds": 6*3600, "desc": "拔管/产后4-6h"},
    {"id": "sys_102", "category": "mom", "task": "【产后】下床活动", "offset_seconds": 24*3600, "desc": "预防血栓"},
    {"id": "sys_103", "category": "mom", "task": "【护理】会阴/伤口消毒", "offset_seconds": 24*3600, "desc": "每日2次"},
    {"id": "sys_104", "category": "mom", "task": "【乳房】生理性涨奶冷敷", "offset_seconds": 72*3600, "desc": "产后3-4天"},
    {"id": "sys_105", "category": "mom", "task": "【检查】产后42天检查", "offset_seconds": 42*24*3600, "desc": "盆底肌复查"},
]

# --- 2. 工具函数 ---
def format_timedelta(td):
    total_seconds = int(td.total_seconds())
    is_neg = total_seconds < 0
    total_seconds = abs(total_seconds)
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    time_str = f"{days}天 {hours}小时 {minutes}分 {seconds}秒"
    return f"-{time_str}" if is_neg else time_str

def get_bj_time():
    return datetime.now(BJ_TZ)

def get_user_data_file(username):
    return f"data_{username}.json"

# --- 3. 八字五行计算核心逻辑 ---
def calculate_bazi_info(birth_datetime):
    if not HAS_LUNAR_LIB:
        return None
    
    # 将 datetime 转为 Solar 对象
    solar = Solar.fromYmdHms(
        birth_datetime.year, 
        birth_datetime.month, 
        birth_datetime.day, 
        birth_datetime.hour, 
        birth_datetime.minute, 
        birth_datetime.second
    )
    lunar = solar.getLunar()
    
    # 获取八字 (天干地支)
    bazi_list = lunar.getBaZi() # ['甲辰', '丙寅'...]
    
    # 获取八字的五行属性 (例如: YearGanWuXing='木')
    # 顺序：年干, 年支, 月干, 月支, 日干, 日支, 时干, 时支
    wuxing_elements = [
        lunar.getYearGanWuXing(), lunar.getYearZhiWuXing(),
        lunar.getMonthGanWuXing(), lunar.getMonthZhiWuXing(),
        lunar.getDayGanWuXing(), lunar.getDayZhiWuXing(),
        lunar.getTimeGanWuXing(), lunar.getTimeZhiWuXing()
    ]
    
    # 统计五行数量
    counts = {"金": 0, "木": 0, "水": 0, "火": 0, "土": 0}
    for w in wuxing_elements:
        if w in counts:
            counts[w] += 1
            
    # 找出缺少的五行
    missing = [k for k, v in counts.items() if v == 0]
    
    return {
        "lunar_str": f"{lunar.getYearInGanZhi()}年 {lunar.getMonthInGanZhi()}月 {lunar.getDayInGanZhi()}日 {lunar.getTimeZhi()}时",
        "bazi": bazi_list, # [年柱, 月柱, 日柱, 时柱]
        "wuxing_list": wuxing_elements,
        "counts": counts,
        "missing": missing,
        "animal": lunar.getYearShengXiao() # 生肖
    }

# --- 4. 账号与数据管理系统 ---
def init_user_system():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f: json.dump({}, f)

def register_user(username, password):
    init_user_system()
    with open(USERS_FILE, 'r') as f: users = json.load(f)
    if username in users: return False, "用户已存在"
    users[username] = password
    with open(USERS_FILE, 'w') as f: json.dump(users, f)
    return True, "注册成功"

def login_user(username, password):
    init_user_system()
    with open(USERS_FILE, 'r') as f: users = json.load(f)
    return users.get(username) == password

def load_user_data(username):
    filename = get_user_data_file(username)
    if not os.path.exists(filename):
        return {"birth_time": None, "tasks": {}, "custom_templates": []}
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_user_data(username, data):
    filename = get_user_data_file(username)
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_all_templates(user_data):
    custom = user_data.get("custom_templates", [])
    return DEFAULT_TEMPLATE + custom

# --- 5. 界面组件 ---
st.set_page_config(page_title="新生儿任务管家 Pro", page_icon="🍼", layout="centered")

def render_login_page():
    st.markdown("## 🔐 登录 / 注册")
    tab1, tab2 = st.tabs(["登录", "新用户注册"])
    with tab1:
        username = st.text_input("账号", key="login_user")
        password = st.text_input("密码", type="password", key="login_pw")
        if st.button("登录"):
            if login_user(username, password):
                st.session_state['logged_in'] = True
                st.session_state['username'] = username
                st.success("登录成功！")
                st.rerun()
            else:
                st.error("账号或密码错误")
    with tab2:
        new_user = st.text_input("设置新账号", key="reg_user")
        new_pw = st.text_input("设置密码", type="password", key="reg_pw")
        if st.button("注册"):
            if new_user and new_pw:
                success, msg = register_user(new_user, new_pw)
                if success:
                    st.success(msg + "，请切换到登录页登录。")
                else:
                    st.error(msg)
            else:
                st.warning("请输入账号和密码")

def render_task_card(task_item, current_time, user_data, username, loc_suffix):
    task_meta = task_item["meta"]
    due_time = task_item["due_time"]
    is_overdue = task_item["is_overdue"]
    status_str = task_item["status_str"]
    task_id = str(task_meta["id"])

    with st.container(border=True):
        col_content, col_action = st.columns([3.5, 1])
        with col_content:
            icon = '👶' if task_meta['category'] == 'baby' else '👩'
            title_color = "red" if is_overdue else ("orange" if (due_time - current_time).total_seconds() < 12*3600 else "blue")
            st.markdown(f"**{icon} :{title_color}[{task_meta['task']}]**")
            status_icon = '🔴' if is_overdue else '🟢'
            st.caption(f"{status_icon} {status_str} | 截止: {due_time.strftime('%m-%d %H:%M')}")
            if task_meta['desc']: st.caption(f"💡 {task_meta['desc']}")
            note_key = f"note_{task_id}_{loc_suffix}"
            note = st.text_input("备注", key=note_key, placeholder="记录数值/情况...", label_visibility="collapsed")

        with col_action:
            st.write("") 
            btn_key = f"btn_{task_id}_{loc_suffix}"
            if st.button("✅ 完成", key=btn_key):
                user_data["tasks"][task_id] = {
                    "status": "done",
                    "done_at": current_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "note": note
                }
                save_user_data(username, user_data)
                st.toast(f"{task_meta['task']} 已归档！")
                st.rerun()

# 视图 A: 顶部时钟 + 八字五行 (每1秒刷新)
@st.fragment(run_every=1)
def render_header_clock(username):
    user_data = load_user_data(username)
    if not user_data["birth_time"]: return 
    
    birth_time = datetime.strptime(user_data["birth_time"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=BJ_TZ)
    now = get_bj_time()
    age_delta = now - birth_time
    
    st.info(f"📅 宝宝已出生: **{format_timedelta(age_delta)}**\n\n🕒 当前时间: {now.strftime('%H:%M:%S')}")

    # --- 八字五行模块 ---
    with st.expander("🔮 查看宝宝八字五行 (点击展开)", expanded=False):
        if not HAS_LUNAR_LIB:
            st.warning("⚠️ 请在终端运行 `pip install lunar_python` 以启用八字计算功能。")
        else:
            info = calculate_bazi_info(birth_time)
            if info:
                # 1. 八字展示
                st.markdown(f"**☯️ 生肖**: {info['animal']} | **农历**: {info['lunar_str']}")
                
                c1, c2, c3, c4 = st.columns(4)
                cols = [c1, c2, c3, c4]
                titles = ["年柱 (父母)", "月柱 (兄弟)", "日柱 (命主)", "时柱 (子女)"]
                
                for i in range(4):
                    gan_wuxing = info['wuxing_list'][i*2]
                    zhi_wuxing = info['wuxing_list'][i*2+1]
                    gan_zhi = info['bazi'][i]
                    with cols[i]:
                        st.caption(titles[i])
                        st.markdown(f"#### {gan_zhi}")
                        st.text(f"{gan_wuxing} / {zhi_wuxing}")

                st.divider()
                
                # 2. 五行统计
                st.write("**🌀 五行强弱统计**:")
                wc1, wc2, wc3, wc4, wc5 = st.columns(5)
                w_map = [("金", "🪙"), ("木", "🌲"), ("水", "💧"), ("火", "🔥"), ("土", "⛰️")]
                
                for idx, (element, icon) in enumerate(w_map):
                    count = info['counts'][element]
                    with [wc1, wc2, wc3, wc4, wc5][idx]:
                        st.metric(f"{icon} {element}", count)
                
                # 3. 缺失提醒
                if info['missing']:
                    st.error(f"⚠️ **五行缺**: {'、'.join(info['missing'])}")
                else:
                    st.success("✅ **五行俱全**，平衡安康！")

# 视图 B: 任务列表
@st.fragment(run_every=60)
def render_task_lists(username):
    user_data = load_user_data(username)
    if not user_data["birth_time"]: return

    birth_time = datetime.strptime(user_data["birth_time"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=BJ_TZ)
    now = get_bj_time()
    all_templates = get_all_templates(user_data)
    pending_tasks = []
    
    for task in all_templates:
        task_id = str(task["id"])
        record = user_data["tasks"].get(task_id)
        if record and record["status"] == "done": continue 
        due_time = birth_time + timedelta(seconds=task["offset_seconds"])
        is_overdue = now > due_time
        time_diff = due_time - now if not is_overdue else now - due_time
        time_str = format_timedelta(time_diff)
        status_str = f"已超期 {time_str}" if is_overdue else f"剩余 {time_str}"
        pending_tasks.append({
            "meta": task,
            "due_time": due_time,
            "is_overdue": is_overdue,
            "status_str": status_str
        })
        
    pending_tasks.sort(key=lambda x: x["due_time"])
    
    tab_home, tab_baby, tab_mom = st.tabs(["🏠 总览", "👶 宝宝待办", "👩 妈妈待办"])
    
    with tab_home:
        if not pending_tasks:
            st.balloons()
            st.success("目前没有待办事项！")
        for item in pending_tasks:
            render_task_card(item, now, user_data, username, "home")
    with tab_baby:
        items = [t for t in pending_tasks if t["meta"]["category"] == "baby"]
        if not items: st.info("无宝宝待办")
        for item in items: render_task_card(item, now, user_data, username, "baby")
    with tab_mom:
        items = [t for t in pending_tasks if t["meta"]["category"] == "mom"]
        if not items: st.info("无妈妈待办")
        for item in items: render_task_card(item, now, user_data, username, "mom")

# 视图 C: 历史记录
def render_history_view(username, user_data):
    st.header("📜 历史完成记录")
    col1, col2 = st.columns([3, 1])
    with col1: st.caption("这里展示所有已完成的任务。")
    with col2:
        if st.button("🔄 刷新表格"): st.rerun()

    completed_list = []
    all_tmps = get_all_templates(user_data)
    for t_id, record in user_data["tasks"].items():
        if record["status"] == "done":
            task_detail = next((t for t in all_tmps if str(t["id"]) == t_id), None)
            task_name = task_detail["task"] if task_detail else "未知/已删任务"
            category = task_detail["category"] if task_detail else "other"
            completed_list.append({
                "分类": "👶" if category=="baby" else ("👩" if category=="mom" else "📝"),
                "任务": task_name,
                "完成时间": record["done_at"],
                "备注": record.get("note", "")
            })
    if completed_list:
        df = pd.DataFrame(completed_list).sort_values("完成时间", ascending=False)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("暂无历史记录")

# 视图 D: 设置
def render_settings_view(username, user_data):
    st.header("⚙️ 任务管理与设置")
    st.subheader("1. 新增自定义待办")
    with st.container(border=True):
        with st.form("add_task_form"):
            c1, c2 = st.columns(2)
            new_task_name = c1.text_input("任务名称", placeholder="例如：去拍百天照")
            new_task_cat = c2.selectbox("分类", ["baby", "mom"])
            new_task_desc = st.text_input("说明", placeholder="简短描述")
            st.write("⏱️ 触发时间 (出生后多久)：")
            tc1, tc2, tc3 = st.columns(3)
            d_off = tc1.number_input("天", min_value=0, value=0)
            h_off = tc2.number_input("小时", min_value=0, value=0)
            m_off = tc3.number_input("分钟", min_value=0, value=0)
            if st.form_submit_button("➕ 添加", type="primary"):
                if new_task_name:
                    total_seconds = d_off*86400 + h_off*3600 + m_off*60
                    new_id = f"custom_{uuid.uuid4().hex[:8]}"
                    new_item = {
                        "id": new_id,
                        "category": new_task_cat,
                        "task": new_task_name,
                        "offset_seconds": total_seconds,
                        "desc": new_task_desc
                    }
                    user_data.setdefault("custom_templates", []).append(new_item)
                    save_user_data(username, user_data)
                    st.success("任务添加成功！")
                    time.sleep(1)
                    st.rerun()
                else: st.error("请输入任务名称")

    st.subheader("2. 危险区域")
    with st.container(border=True):
        if 'confirm_delete' not in st.session_state: st.session_state.confirm_delete = False
        if not st.session_state.confirm_delete:
            if st.button("🗑️ 清空当前账号数据"):
                st.session_state.confirm_delete = True
                st.rerun()
        else:
            st.warning("⚠️ 确定要删除吗？此操作无法撤销！")
            col_y, col_n = st.columns(2)
            with col_y:
                if st.button("✅ 确认删除", type="primary"):
                    user_data["birth_time"] = None
                    user_data["tasks"] = {}
                    user_data["custom_templates"] = []
                    save_user_data(username, user_data)
                    st.session_state.confirm_delete = False
                    st.success("数据已重置")
                    st.rerun()
            with col_n:
                if st.button("❌ 取消"):
                    st.session_state.confirm_delete = False
                    st.rerun()

# --- 6. 主程序逻辑 ---
def main():
    if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
    if not st.session_state['logged_in']:
        render_login_page()
        return

    username = st.session_state['username']
    user_data = load_user_data(username)

    with st.sidebar:
        st.write(f"👋 你好, **{username}**")
        selected_view = st.radio("功能导航", ["📌 任务看板", "📜 历史记录", "⚙️ 任务管理"], index=0)
        st.divider()
        if st.button("🚪 退出登录"):
            st.session_state['logged_in'] = False
            st.rerun()

    if not user_data["birth_time"]:
        st.warning(f"欢迎新用户，请先设置宝宝出生时间")
        now_bj = get_bj_time()
        col1, col2 = st.columns(2)
        d = col1.date_input("出生日期", value=now_bj)
        t = col2.time_input("出生时间", value=now_bj)
        if st.button("🚀 开始记录"):
            birth_dt = datetime.combine(d, t).replace(tzinfo=BJ_TZ)
            user_data["birth_time"] = birth_dt.strftime("%Y-%m-%d %H:%M:%S")
            save_user_data(username, user_data)
            st.rerun()
        return

    if selected_view == "📌 任务看板":
        render_header_clock(username)
        st.divider()
        render_task_lists(username)
    elif selected_view == "📜 历史记录":
        render_history_view(username, user_data)
    elif selected_view == "⚙️ 任务管理":
        render_settings_view(username, user_data)

if __name__ == "__main__":
    main()

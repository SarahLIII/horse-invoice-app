import streamlit as st
import pandas as pd
import datetime
from datetime import date, timedelta
import smtplib
from email.mime.text import MIMEText



# 页面标题
st.set_page_config(page_title="智能月度账单系统", layout="wide")
st.title("🏇 智能月度账单系统")

# 1) 基础日费率输入
rate = st.number_input(
    label="基础日费率（$/天）",
    min_value=0.0,
    value=50.0,
    step=1.0
)

# 2) 上传参赛费用表
st.write("上传参赛费用 CSV（必须包含列：horse_id, fee_date, amount）")
comp_file = st.file_uploader(label="比赛费用表", type=["csv"])
if comp_file:
    comp_df = pd.read_csv(comp_file, parse_dates=["fee_date"])
else:
    comp_df = None

# 3) 上传马主信息表
st.write("上传马主信息 CSV（必须包含列：horse_id, owner_name, owner_email）")
owner_file = st.file_uploader(label="马主信息表", type=["csv"])
if owner_file:
    owner_df = pd.read_csv(owner_file)
else:
    owner_df = None
import datetime
from datetime import date, timedelta

# …前面读取 rate、comp_df、owner_df 的代码保持不变…

# —— 全局：计算 ym、days ——
today = date.today()
first_of_this = today.replace(day=1)
last_of_prev = first_of_this - timedelta(days=1)
ym   = last_of_prev.strftime("%Y-%m")
days = last_of_prev.day

# —— 全局：生成一份 invoice_df，包含 base_fee, comp_fee, total ——
if owner_df is not None:
    invoice_df = owner_df.copy()  # 复制原始表
    # 2) 基础费
    invoice_df["base_fee"] = rate * days

    # 3) 比赛费合计
    if comp_df is not None:
        comp_df["fee_date"] = pd.to_datetime(comp_df["fee_date"], errors="coerce")
        mask = comp_df["fee_date"].dt.strftime("%Y-%m") == ym
        comp_sum = (
            comp_df[mask]
            .groupby("horse_id")["amount"]
            .sum()
            .reset_index()
            .rename(columns={"amount": "comp_fee"})
        )
        invoice_df = invoice_df.merge(comp_sum, on="horse_id", how="left")
    invoice_df["comp_fee"] = invoice_df.get("comp_fee", 0).fillna(0)

    # 4) 总费用
    invoice_df["total"] = invoice_df["base_fee"] + invoice_df["comp_fee"]
else:
    invoice_df = None


# 4) 预览账单
if st.button("📄 生成并预览上月账单"):
    if invoice_df is None:
        st.error("❌ 请先上传马主信息表！")
    else:
        st.dataframe(invoice_df[["owner_name","owner_email","base_fee","comp_fee","total"]])

# 5) 发送邮件
if st.button("✉️ 发送账单邮件"):
    if invoice_df is None:
        st.error("❌ 请先生成并预览账单后再发邮件！")
    else:
        try:
            smtp = smtplib.SMTP(
                st.secrets["smtp"]["server"],
                st.secrets["smtp"]["port"]
            )
            smtp.starttls()
            smtp.login(
                st.secrets["smtp"]["user"],
                st.secrets["smtp"]["password"]
            )
            for _, r in invoice_df.iterrows():
                name  = r["owner_name"]
                email = r["owner_email"]
                base  = r["base_fee"]
                comp  = r["comp_fee"]
                total = r["total"]
                body = f"""
Dear {name},

Please find below your invoice for horse boarding services for {ym}:

Base boarding fee ({days} days): ${base:.2f}

Competition fees: ${comp:.2f}

Total amount due: ${total:.2f}

If you have any questions, feel free to reply to this email.

Best regards,
[Your Name]
"""
                msg = MIMEText(body)
                msg["Subject"] = f"{ym} Horse Boarding Invoice"
                msg["From"] = st.secrets["smtp"]["user"]
                msg["To"] = email
                smtp.send_message(msg)
            smtp.quit()
            st.success("✅ All emails sent successfully!")
        except Exception as e:
            st.error(f"❌ Failed to send emails: {e}")
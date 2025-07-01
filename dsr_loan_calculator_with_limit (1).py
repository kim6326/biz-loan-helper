import streamlit as st
import re

st.set_page_config(
    page_title="DSR 담보계산기",
    page_icon="🏦",
    layout="wide"
)

def comma_number_input(label, key, value="0"):
    user_input = st.text_input(label, value=value, key=key)
    digits_only = re.sub(r'[^0-9]', '', user_input)
    formatted = f"{int(digits_only):,}" if digits_only else ""
    st.markdown(f"<div style='color:gray; font-size:0.9em;'>입력값: {formatted}</div>", unsafe_allow_html=True)
    return int(digits_only) if digits_only else 0

def calculate_monthly_payment(principal, annual_rate, years):
    if years <= 0:
        return 0
    monthly_rate = annual_rate / 100 / 12
    months = years * 12
    if monthly_rate == 0:
        return principal / months
    return principal * (monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)

LTV_MAP = {
    "서울": 0.70,
    "경기/인천": 0.65,
    "기타": 0.60
}

STRESS_RATE_MAP = {
    "고정형": 1.0,
    "혼합형 (80%)": 1.8,
    "혼합형 (60%)": 1.6,
    "혼합형 (40%)": 1.4,
    "주기형 (40%)": 1.4,
    "주기형 (30%)": 1.3,
    "주기형 (20%)": 1.2
}

st.title("🏦 DSR 담보계산기 (스트레스 DSR 반영)")

annual_income = comma_number_input("연소득을 입력하세요", key="annual_income")
region = st.selectbox("지역을 선택하세요", list(LTV_MAP.keys()))
apt_price = comma_number_input("아파트 시세 (KB 시세 기준)", key="apt_price")
first_home = st.checkbox("내생에 최초 주택 구입 여부 (생애최초)")

# ✅ 생애최초 시 70% 적용
if first_home:
    ltv_ratio = 0.70
    max_ltv_limit = apt_price * ltv_ratio
else:
    ltv_ratio = LTV_MAP.get(region, 0.6)
    max_ltv_limit = apt_price * ltv_ratio

loan_type = st.selectbox("금리 구조를 선택하세요", list(STRESS_RATE_MAP.keys()))
stress_multiplier = STRESS_RATE_MAP[loan_type]

st.subheader("기존 대출 내역")
existing_loans = []
num_loans = st.number_input("기존 대출 항목 수", min_value=0, max_value=10, value=0)
for i in range(num_loans):
    st.markdown(f"**대출 {i+1}**")
    amount = comma_number_input(f"대출 {i+1} 금액", key=f"amount_{i}")
    rate = st.number_input(f"대출 {i+1} 연이자율 (%)", min_value=0.0, format="%.2f", key=f"rate_{i}")
    years = st.number_input(f"대출 {i+1} 기간 (년)", min_value=0, key=f"years_{i}")
    existing_loans.append({"amount": amount, "rate": rate, "years": years})

st.subheader("신규 대출 조건")
desired_amount = comma_number_input("신규 대출 희망 금액", key="new_loan")
base_rate = st.number_input("기본 대출 금리 (%)", value=4.7, format="%.2f")
term = st.number_input("대출 기간 (년)", value=30)

if st.button("계산하기"):
    total_existing_monthly = sum(
        calculate_monthly_payment(loan["amount"], loan["rate"], loan["years"])
        for loan in existing_loans
    )
    st.markdown(f"**총 기존 대출 월 상환액:** {total_existing_monthly:,.0f} 원")

    dsr_limit = annual_income * 0.4 / 12
    available_payment = max(0, dsr_limit - total_existing_monthly)
    st.markdown(f"**DSR 한도 내 여유 월 상환 가능액:** {available_payment:,.0f} 원")

    stressed_rate = base_rate * stress_multiplier
    monthly_rate = stressed_rate / 100 / 12
    months = term * 12

    if monthly_rate > 0:
        max_loan = available_payment * ((1 + monthly_rate) ** months - 1) / (monthly_rate * ((1 + monthly_rate) ** months))
    else:
        max_loan = available_payment * months

    ltv_limit = min(max_ltv_limit, apt_price * ltv_ratio)

    st.markdown("---")
    st.markdown(f"🏠 **아파트 시세:** {apt_price:,.0f} 원")
    st.markdown(f"🔒 **LTV 기준 최대 대출 가능액:** {ltv_limit:,.0f} 원")
    st.markdown(f"📈 **스트레스 적용 금리:** {stressed_rate:.2f}%")
    st.markdown(f"💰 **DSR 기준 최대 대출 가능액:** {max_loan:,.0f} 원")

    final_limit = min(max_loan, ltv_limit)
    st.success(f"📌 **최종 대출 가능 금액:** {final_limit:,.0f} 원")



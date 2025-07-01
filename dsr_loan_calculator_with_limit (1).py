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
    return principal * (monthly_rate * (1 + monthly_rate)**months) / ((1 + monthly_rate)**months - 1)

LTV_MAP = {
    "서울": 0.70,
    "경기": 0.65,
    "인천": 0.65,
    "지방": 0.60,
}

st.title("🏦 DSR 담보계산기 (스트레스 적용 포함)")

annual_income = comma_number_input("연소득을 입력하세요", key="annual_income", value="")

region = st.selectbox("지역을 선택하세요", list(LTV_MAP.keys()))
use_custom_ltv = st.checkbox("LTV 직접 입력하기")
first_home = st.checkbox("내생에 최초 주택 구입 여부 (생애최초)")

if use_custom_ltv:
    if first_home:
        st.markdown("<span style='color:gray;'>※ 생애최초 주택 구입자는 LTV 70%로 자동 설정됩니다.</span>", unsafe_allow_html=True)
        ltv_ratio = 0.7
    else:
        ltv_ratio = st.number_input("직접 입력한 LTV 비율 (%)", min_value=0.0, max_value=100.0, value=60.0, step=0.1) / 100
else:
    ltv_ratio = LTV_MAP.get(region, 0.6)

apt_price = comma_number_input("아파트 시세 (KB 시세 기준)", key="apt_price")
if apt_price:
    st.markdown(f"<div style='color:gray; font-size:0.9em;'>입력된 아파트 시세: {apt_price:,} 원</div>", unsafe_allow_html=True)

existing_loans = []
num_loans = st.number_input("기존 대출 항목 수", min_value=0, max_value=10, value=0)

for i in range(num_loans):
    st.markdown(f"**대출 {i+1}**")
    amount = comma_number_input(f"대출 {i+1} 금액", key=f"amount_{i}")
    rate = st.number_input(f"대출 {i+1} 연이자율 (%)", min_value=0.0, format="%.2f", key=f"rate_{i}")
    years = st.number_input(f"대출 {i+1} 기간 (년)", min_value=0, key=f"years_{i}")
    existing_loans.append({"amount": amount, "rate": rate, "years": years})

st.subheader("신규 대출 희망 조건")
new_loan_amount = comma_number_input("희망 신규 대출 금액", key="new_loan")
new_loan_rate = st.number_input("희망 신규 대출 연이자율 (%)", min_value=0.0, format="%.2f")
new_loan_years = st.number_input("희망 신규 대출 기간 (년)", min_value=0)

loan_type = st.selectbox("대출 금리 유형", ["고정형", "변동형", "혼합형", "주기형"])
if loan_type == "고정형":
    stress_multiplier = 1.0
elif loan_type == "변동형":
    stress_multiplier = 2.0
elif loan_type == "혼합형":
    stress_multiplier = 1.8
elif loan_type == "주기형":
    stress_multiplier = 1.6
else:
    stress_multiplier = 1.0

DSR_RATIO = 0.4

if st.button("계산하기"):
    total_existing_monthly = 0
    st.write("## 기존 대출 월 상환액")
    for idx, loan in enumerate(existing_loans):
        monthly_payment = calculate_monthly_payment(loan["amount"], loan["rate"], loan["years"])
        st.write(f"대출 {idx+1}: {monthly_payment:,.0f} 원")
        total_existing_monthly += monthly_payment

    st.write(f"**총 기존 대출 월 상환액: {total_existing_monthly:,.0f} 원**")
    dsr_limit = (annual_income / 12) * DSR_RATIO
    st.write(f"DSR 한도 (연소득 × {DSR_RATIO*100}%): {dsr_limit:,.0f} 원")

    available_payment = dsr_limit - total_existing_monthly

    ltv_limit_raw = apt_price * ltv_ratio
    ltv_limit = ltv_limit_raw
    if first_home and ltv_limit > 600_000_000:
        ltv_limit = 600_000_000

    st.write(f"LTV 기준 최대 대출 가능액: {ltv_limit:,.0f} 원")
    st.write(f"(원래 LTV 한도: {ltv_limit_raw:,.0f} 원)")

    stress_rate = new_loan_rate * stress_multiplier
    new_loan_monthly = calculate_monthly_payment(new_loan_amount, stress_rate, new_loan_years)
    st.write(f"신규 대출 월 상환액 (스트레스 적용 {stress_rate:.2f}%): {new_loan_monthly:,.0f} 원")

    if new_loan_amount <= ltv_limit and new_loan_monthly <= available_payment:
        st.success("✅ 신규 대출 실행 가능!")
    else:
        st.error("❌ 신규 대출 실행 불가.")

st.subheader("📊 신규 대출 최대 가능 금액 계산기")
calc_rate = st.number_input("계산용 연이자율 (%)", value=4.7, key="calc_rate")
calc_years = st.number_input("계산용 대출 기간 (년)", value=30, key="calc_years")

if st.button("최대 대출 가능 금액 계산"):
    total_existing_monthly = sum(
        calculate_monthly_payment(loan["amount"], loan["rate"], loan["years"]) for loan in existing_loans
    )
    dsr_limit = (annual_income / 12) * DSR_RATIO
    available_payment = dsr_limit - total_existing_monthly
    calc_stress_rate = calc_rate * stress_multiplier
    monthly_rate = calc_stress_rate / 100 / 12
    months = calc_years * 12

    max_loan = 0
    if available_payment > 0:
        if monthly_rate > 0:
            max_loan = available_payment * ((1 + monthly_rate)**months - 1) / (monthly_rate * (1 + monthly_rate)**months)
        else:
            max_loan = available_payment * months

    if max_loan > 0:
        st.success(f"📌 최대 대출 가능 금액: {max_loan:,.0f} 원 ({calc_years}년, 스트레스 금리 {calc_stress_rate:.2f}%)")
        st.info(f"💡 LTV 기준 최대 대출 가능액: {ltv_limit:,.0f} 원")
        st.info(f"🏠 아파트 시세: {apt_price:,.0f} 원")
    else:
        st.error("❌ 현재 조건에서는 추가 대출이 불가능합니다.")
        st.info("기존 대출을 줄이거나 연소득을 높이시면 대출이 가능해질 수 있습니다.")

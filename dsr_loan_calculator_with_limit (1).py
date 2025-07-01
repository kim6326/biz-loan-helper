import streamlit as st
import re

st.set_page_config(
    page_title="DSR 담보계산기 (스트레스 DSR 적용)",
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
    payment = principal * (monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)
    return payment

LTV_MAP = {"서울": 0.70, "경기": 0.65, "부산": 0.60, "기타": 0.60}

st.title("🏦 DSR 담보계산기 (스트레스 DSR 적용)")

annual_income = comma_number_input("연소득을 입력하세요", key="annual_income", value="")
region = st.selectbox("지역을 선택하세요", list(LTV_MAP.keys()))
use_custom_ltv = st.checkbox("LTV 직접 입력하기")
first_home = st.checkbox("내생에 최초 주택 구입 여부 (생애최초)")

if use_custom_ltv:
    ltv_ratio = st.number_input("직접 입력한 LTV 비율 (%)", min_value=0.0, max_value=100.0, value=60.0, step=0.1) / 100
else:
    if first_home:
        ltv_ratio = 0.70
    else:
        ltv_ratio = LTV_MAP.get(region, 0.6)

apt_price = comma_number_input("아파트 시세 (KB 시세 기준)", key="apt_price")
if apt_price:
    st.markdown(f"<div style='color:gray; font-size:0.9em;'>입력된 아파트 시세: {apt_price:,} 원</div>", unsafe_allow_html=True)

st.subheader("기존 대출 내역 추가")
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
loan_type = st.selectbox("신규 대출 유형 선택", ["고정형", "변동형", "혼합형"])

# 스트레스 금리 설정
stress_rate = new_loan_rate
if loan_type == "변동형":
    stress_rate += 2.0
elif loan_type == "혼합형":
    stress_rate += 1.0  # 예시: 혼합형은 1% 가산

DSR_RATIO = 0.4

if st.button("계산하기"):
    total_existing_monthly = 0
    for loan in existing_loans:
        total_existing_monthly += calculate_monthly_payment(loan["amount"], loan["rate"], loan["years"])
    dsr_limit = (annual_income / 12) * DSR_RATIO
    available_payment = dsr_limit - total_existing_monthly

    ltv_limit_raw = apt_price * ltv_ratio
    ltv_limit = min(ltv_limit_raw, 600_000_000) if first_home else ltv_limit_raw

    new_loan_monthly = calculate_monthly_payment(new_loan_amount, stress_rate, new_loan_years)

    st.write(f"DSR 한도: {dsr_limit:,.0f} 원")
    st.write(f"총 기존 대출 월 상환액: {total_existing_monthly:,.0f} 원")
    st.write(f"여유 상환 가능액: {available_payment:,.0f} 원")
    st.write(f"스트레스 금리 적용 월 상환액: {new_loan_monthly:,.0f} 원")
    st.write(f"LTV 기준 최대 대출 가능액: {ltv_limit:,.0f} 원")

    if new_loan_amount <= ltv_limit and new_loan_monthly <= available_payment:
        st.success("✅ 스트레스 DSR 기준 신규 대출 가능")
    else:
        st.error("❌ 스트레스 DSR 기준 신규 대출 불가")

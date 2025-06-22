import streamlit as st
import re

# 숫자를 자동으로 콤마(,) 처리하는 함수
def format_number_input(label, value="0", key=None):
    raw_input = st.text_input(label, value=value, key=key)
    # 숫자만 추출
    digits_only = re.sub(r'[^0-9]', '', raw_input)
    formatted = f"{int(digits_only):,}" if digits_only else ""
    st.text_input(label + " (자동포맷)", value=formatted, key=f"formatted_{key}", disabled=True)
    try:
        return int(digits_only)
    except:
        return 0

# 원리금 균등상환 월 상환액 계산 함수
def calculate_monthly_payment(principal, annual_rate, years):
    if years <= 0:
        return 0
    monthly_rate = annual_rate / 100 / 12
    months = years * 12
    if monthly_rate == 0:
        return principal / months
    payment = principal * (monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)
    return payment

# 지역별 LTV 비율 (예시)
LTV_MAP = {
    "서울": 0.70,
    "경기": 0.65,
    "부산": 0.60,
    "기타": 0.60,
}

st.title("DSR 기반 담보대출 계산기")

# 1. 연소득 입력 (자리수 자동 포맷)
annual_income = format_number_input("연소득을 입력하세요", value="97000000", key="annual_income")

# 2. 지역 선택
region = st.selectbox("지역을 선택하세요", list(LTV_MAP.keys()))

# 3. 기존 대출 리스트
st.subheader("기존 대출 내역 추가")
existing_loans = []
num_loans = st.number_input("기존 대출 항목 수", min_value=0, max_value=10, value=0)

for i in range(num_loans):
    st.markdown(f"**대출 {i+1}**")
    amount = format_number_input(f"대출 {i+1} 금액", value="0", key=f"amount_{i}")
    rate = st.number_input(f"대출 {i+1} 연이자율 (%)", min_value=0.0, format="%.2f", key=f"rate_{i}")
    years = st.number_input(f"대출 {i+1} 기간 (년)", min_value=0, key=f"years_{i}")
    existing_loans.append({"amount": amount, "rate": rate, "years": years})

# 4. 신규 대출 희망 조건
st.subheader("신규 대출 희망 조건")
new_loan_amount = format_number_input("희망 신규 대출 금액", value="0", key="new_loan")
new_loan_rate = st.number_input("희망 신규 대출 연이자율 (%)", min_value=0.0, format="%.2f")
new_loan_years = st.number_input("희망 신규 대출 기간 (년)", min_value=0)

# DSR 기준 비율
DSR_RATIO = 0.4

# 계산 버튼
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
    st.write(f"여유 상환 가능액: {available_payment:,.0f} 원")
    ltv_limit = new_loan_amount * LTV_MAP.get(region, 0.6)
    st.write(f"지역({region})별 LTV 한도: {ltv_limit:,.0f} 원")

    new_loan_monthly = calculate_monthly_payment(new_loan_amount, new_loan_rate, new_loan_years)
    st.write(f"신규 대출 월 상환액: {new_loan_monthly:,.0f} 원")

    if new_loan_amount <= ltv_limit and new_loan_monthly <= available_payment:
        st.success("신규 대출 실행 가능!")
    else:
        st.error("신규 대출 실행 불가!")

# ✅ 추가: 최대 대출 가능 금액 역산 계산기
st.subheader("신규 대출 최대 가능 금액 계산기")
calc_rate = st.number_input("계산용 연이자율 (%)", value=4.7, key="calc_rate")
calc_years = st.number_input("계산용 대출 기간 (년)", value=30, key="calc_years")

if st.button("최대 대출 가능 금액 계산"):
    calc_monthly_rate = calc_rate / 100 / 12
    calc_months = int(calc_years * 12)
    if calc_monthly_rate > 0:
        max_loan = available_payment * ((1 + calc_monthly_rate)**calc_months - 1) / (calc_monthly_rate * (1 + calc_monthly_rate)**calc_months)
        st.success(f"{calc_years}년, 연 {calc_rate}% 기준으로 최대 대출 가능 금액은 {max_loan:,.0f} 원입니다.")
    else:
        max_loan = available_payment * calc_months
        st.success(f"무이자 조건에서 최대 대출 가능 금액은 {max_loan:,.0f} 원입니다.")


 

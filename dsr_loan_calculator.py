
import streamlit as st

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

# 1. 연소득 입력
annual_income = st.number_input("연소득을 입력하세요 (원)", min_value=0, step=1000000)

# 2. 지역 선택
region = st.selectbox("지역을 선택하세요", list(LTV_MAP.keys()))

# 3. 기존 대출 리스트
st.subheader("기존 대출 내역 추가")
existing_loans = []

# 기존 대출 입력 개수 설정
num_loans = st.number_input("기존 대출 항목 수", min_value=0, max_value=10, value=0)

for i in range(num_loans):
    st.markdown(f"**대출 {i+1}**")
    amount = st.number_input(f"대출 {i+1} 금액 (원)", min_value=0, key=f"amount_{i}")
    rate = st.number_input(f"대출 {i+1} 연이자율 (%)", min_value=0.0, format="%.2f", key=f"rate_{i}")
    years = st.number_input(f"대출 {i+1} 기간 (년)", min_value=0, key=f"years_{i}")
    existing_loans.append({"amount": amount, "rate": rate, "years": years})

# 4. 신규 대출 희망 조건
st.subheader("신규 대출 희망 조건")
new_loan_amount = st.number_input("희망 신규 대출 금액 (원)", min_value=0)
new_loan_rate = st.number_input("희망 신규 대출 연이자율 (%)", min_value=0.0, format="%.2f")
new_loan_years = st.number_input("희망 신규 대출 기간 (년)", min_value=0)

# DSR 기준 비율 (예: 40%)
DSR_RATIO = 0.4

# 계산 버튼
if st.button("계산하기"):

    # 기존 대출 월 상환액 계산
    total_existing_monthly = 0
    st.write("## 기존 대출 월 상환액")
    for idx, loan in enumerate(existing_loans):
        monthly_payment = calculate_monthly_payment(loan["amount"], loan["rate"], loan["years"])
        st.write(f"대출 {idx+1}: {monthly_payment:,.0f} 원")
        total_existing_monthly += monthly_payment

    st.write(f"**총 기존 대출 월 상환액: {total_existing_monthly:,.0f} 원**")

    # DSR 한도 계산
    dsr_limit = (annual_income / 12) * DSR_RATIO
    st.write(f"DSR 한도 (연소득 × {DSR_RATIO*100}%): {dsr_limit:,.0f} 원")

    # 여유 상환 가능액
    available_payment = dsr_limit - total_existing_monthly
    st.write(f"여유 상환 가능액: {available_payment:,.0f} 원")

    # 지역별 LTV 적용 최대 신규 대출 가능액
    ltv_limit = new_loan_amount * LTV_MAP.get(region, 0.6)
    st.write(f"지역({region})별 LTV 한도: {ltv_limit:,.0f} 원")

    # 신규 대출 월 상환액 계산
    new_loan_monthly = calculate_monthly_payment(new_loan_amount, new_loan_rate, new_loan_years)
    st.write(f"신규 대출 월 상환액: {new_loan_monthly:,.0f} 원")

    # 신규 대출 실행 가능 여부
    if new_loan_amount <= ltv_limit and new_loan_monthly <= available_payment:
        st.success("신규 대출 실행 가능!")
    else:
        st.error("신규 대출 실행 불가!")

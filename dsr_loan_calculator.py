
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

# 지역별 기본 LTV 비율 (사용자 수정 가능)
LTV_MAP_DEFAULT = {
    "서울": 70,
    "경기": 60,
    "부산": 60,
    "기타": 60,
}

st.title("DSR 기반 담보대출 계산기")

# 1. 연소득 입력
annual_income = st.number_input("연소득을 입력하세요 (원)", min_value=0, step=1000000)

# 2. 아파트 시세 입력
apt_price = st.number_input("구입 예정 아파트 시세 (원)", min_value=0, step=1000000)

# 3. 지역 선택 및 LTV 입력
region = st.selectbox("지역을 선택하세요", list(LTV_MAP_DEFAULT.keys()))
ltv_input = st.number_input(f"{region} 지역의 적용 LTV (%)", min_value=0.0, max_value=100.0, value=LTV_MAP_DEFAULT[region], step=1.0)

# 4. 기존 대출 리스트
st.subheader("기존 대출 내역 추가")
existing_loans = []
num_loans = st.number_input("기존 대출 항목 수", min_value=0, max_value=10, value=0)

for i in range(num_loans):
    st.markdown(f"**대출 {i+1}**")
    amount = st.number_input(f"대출 {i+1} 금액 (원)", min_value=0, key=f"amount_{i}")
    rate = st.number_input(f"대출 {i+1} 연이자율 (%)", min_value=0.0, format="%.2f", key=f"rate_{i}")
    years = st.number_input(f"대출 {i+1} 기간 (년)", min_value=0, key=f"years_{i}")
    existing_loans.append({"amount": amount, "rate": rate, "years": years})

# 5. 신규 대출 희망 조건
st.subheader("신규 대출 희망 조건")
new_loan_rate = st.number_input("희망 신규 대출 연이자율 (%)", min_value=0.0, format="%.2f")
new_loan_years = st.number_input("희망 신규 대출 기간 (년)", min_value=0)

# 계산 버튼
if st.button("계산하기"):
    # 기존 대출 총 월 상환액
    total_existing_monthly = 0
    st.write("## 기존 대출 월 상환액")
    for idx, loan in enumerate(existing_loans):
        monthly_payment = calculate_monthly_payment(loan["amount"], loan["rate"], loan["years"])
        st.write(f"대출 {idx+1}: {monthly_payment:,.0f} 원")
        total_existing_monthly += monthly_payment
    st.write(f"**총 기존 대출 월 상환액: {total_existing_monthly:,.0f} 원**")

    # DSR 계산
    dsr_limit = (annual_income / 12) * 0.4
    st.write(f"**DSR 한도 (연소득의 40%)**: {dsr_limit:,.0f} 원")

    available_payment = dsr_limit - total_existing_monthly
    st.write(f"**여유 상환 가능액**: {available_payment:,.0f} 원")

    # 지역별 LTV 한도 계산
    ltv_limit = apt_price * (ltv_input / 100)
    st.write(f"**LTV 적용 최대 대출 가능액**: {ltv_limit:,.0f} 원")

    # 여유 상환액으로 가능한 신규 대출 금액 역산
    def calculate_max_loan_from_payment(payment, rate, years):
        if years <= 0 or rate <= 0:
            return payment * years * 12
        r = rate / 100 / 12
        n = years * 12
        return payment * ((1 + r)**n - 1) / (r * (1 + r)**n)

    max_new_loan = calculate_max_loan_from_payment(available_payment, new_loan_rate, new_loan_years)
    st.write(f"**DSR 기준 가능 신규 대출 한도**: {max_new_loan:,.0f} 원")

    # 최종 신규 대출 가능 금액 = min(DSR 기준, LTV 기준)
    final_loan_amount = min(max_new_loan, ltv_limit)
    monthly_payment = calculate_monthly_payment(final_loan_amount, new_loan_rate, new_loan_years)
    st.write(f"### ✅ 최종 신규 대출 가능 금액: {final_loan_amount:,.0f} 원")
    st.write(f"➡️ 예상 월 상환금액: {monthly_payment:,.0f} 원")

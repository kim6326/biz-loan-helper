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

# 지역별 기본 LTV (생애최초가 아닌 경우)
DEFAULT_LTV = {
    "서울": 0.70,
    "경기": 0.60,
    "부산": 0.60,
    "기타": 0.60,
}

st.set_page_config(page_title="DSR 기반 담보대출 계산기", layout="centered")
st.title("📊 DSR 기반 담보대출 계산기")

# 1. 연소득 입력
annual_income = st.number_input("1️⃣ 연소득 (원)", min_value=0, step=1000000)

# 2. 생애최초 여부
first_home = st.checkbox("생애최초 주택 구입 여부", value=False)

# 3. 지역 선택 및 시세 입력
region = st.selectbox("2️⃣ 아파트 위치 지역", list(DEFAULT_LTV.keys()))
home_price = st.number_input("3️⃣ 구입할 아파트 시세 (원)", min_value=0, step=10000000)

# 4. 기존 대출 입력
st.subheader("4️⃣ 기존 대출 내역 입력")
existing_loans = []
num_loans = st.number_input("기존 대출 개수", min_value=0, max_value=10, value=0)

for i in range(num_loans):
    st.markdown(f"**기존 대출 {i+1}**")
    col1, col2, col3 = st.columns(3)
    with col1:
        amount = st.number_input(f"금액(원)", min_value=0, key=f"amount_{i}")
    with col2:
        rate = st.number_input(f"이자율(%)", min_value=0.0, key=f"rate_{i}")
    with col3:
        years = st.number_input(f"기간(년)", min_value=1, key=f"years_{i}")
    existing_loans.append({"amount": amount, "rate": rate, "years": years})

# 5. 신규 대출 조건 입력
st.subheader("5️⃣ 신규 대출 조건")
desired_loan = st.number_input("희망 대출 금액 (원)", min_value=0)
desired_rate = st.number_input("희망 대출 이자율 (%)", min_value=0.0, format="%.2f")
desired_years = st.number_input("희망 대출 기간 (년)", min_value=1)

# 6. 수동 LTV 입력 (기본값은 지역별 자동 적용)
manual_ltv = st.number_input("6️⃣ LTV 비율 (자동: 지역 기반, 수동 조정 가능)", min_value=0.0, max_value=1.0, value=DEFAULT_LTV[region] if not first_home else 0.8)

# 7. 계산 실행
if st.button("📌 계산하기"):

    st.write("## ✅ 계산 결과")

    # 기존 대출 월 상환액 계산
    total_existing_monthly = 0
    st.write("### 💳 기존 대출 월 상환액")
    for idx, loan in enumerate(existing_loans):
        monthly_payment = calculate_monthly_payment(loan["amount"], loan["rate"], loan["years"])
        st.write(f"- 대출 {idx+1}: {monthly_payment:,.0f} 원")
        total_existing_monthly += monthly_payment
    st.write(f"**총 월 상환액:** {total_existing_monthly:,.0f} 원")

    # DSR 한도
    DSR_RATIO = 0.4
    dsr_limit = (annual_income / 12) * DSR_RATIO
    st.write(f"### 🧮 DSR 한도: {dsr_limit:,.0f} 원")

    # 여유 상환 가능액
    available_payment = dsr_limit - total_existing_monthly
    st.write(f"**여유 상환 가능액:** {available_payment:,.0f} 원")

    # 신규 대출 상환액
    new_loan_monthly = calculate_monthly_payment(desired_loan, desired_rate, desired_years)
    st.write(f"**신규 대출 월 상환액:** {new_loan_monthly:,.0f} 원")

    # LTV 기준 최대 가능 대출
    ltv_limit = home_price * manual_ltv
    st.write(f"**LTV 한도 (시세 × {manual_ltv*100:.0f}%):** {ltv_limit:,.0f} 원")

    # 신규 대출 실행 가능 여부
    if desired_loan <= ltv_limit and new_loan_monthly <= available_payment:
        st.success("🎉 신규 대출 실행 가능합니다!")
    else:
        st.error("🚫 신규 대출 실행이 어렵습니다. 조건을 조정해보세요.")

# Footer
st.markdown("---")
st.caption("개발자: kim6326 | Streamlit 기반 개인용 도구")
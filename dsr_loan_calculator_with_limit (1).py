import streamlit as st

# 월 상환금 계산 함수 (원리금 균등상환)
def calculate_monthly_payment(principal, annual_rate, years):
    if years <= 0:
        return 0
    monthly_rate = annual_rate / 100 / 12
    months = years * 12
    if monthly_rate == 0:
        return principal / months
    payment = principal * (monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)
    return payment

# 역으로 월 상환금으로 최대 대출 원금 계산
def calculate_max_loan_from_payment(payment, annual_rate, years):
    if years <= 0:
        return 0
    r = annual_rate / 100 / 12
    n = years * 12
    if r == 0:
        return payment * n
    return payment * ((1 + r)**n - 1) / (r * (1 + r)**n)

st.set_page_config(page_title="DSR 기반 담보대출 계산기", layout="centered")
st.title("📊 DSR 기반 담보대출 계산기")

# 1. 연소득 입력
annual_income = st.number_input("1️⃣ 연소득 (원)", min_value=0, step=1000000)

# 2. 생애최초 여부
first_home = st.checkbox("생애최초 주택 구입 여부", value=False)

# 3. 지역 선택 및 시세 입력
DEFAULT_LTV = {
    "서울": 0.70,
    "경기": 0.65,
    "부산": 0.60,
    "기타": 0.60,
}
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

# 6. LTV 설정
ltv_auto = DEFAULT_LTV.get(region, 0.60)
if first_home:
    ltv_auto = max(ltv_auto, 0.80)
ltv = st.number_input("6️⃣ 적용 LTV 비율 (%)", min_value=0.0, max_value=100.0, value=ltv_auto * 100, format="%.1f") / 100

# 7. 계산 실행
if st.button("📌 계산하기"):

    # 기존 대출 월 상환액 합산
    total_existing_monthly = 0
    st.write("### 💳 기존 대출 월 상환액")
    for idx, loan in enumerate(existing_loans):
        m = calculate_monthly_payment(loan["amount"], loan["rate"], loan["years"])
        st.write(f"- 대출 {idx+1}: {m:,.0f} 원")
        total_existing_monthly += m
    st.write(f"**총 월 상환액:** {total_existing_monthly:,.0f} 원")

    # DSR 한도 및 여유액
    dsr_limit = (annual_income / 12) * 0.4
    st.write(f"### 🧮 DSR 한도: {dsr_limit:,.0f} 원")
    available_payment = dsr_limit - total_existing_monthly
    st.write(f"**여유 상환 가능액:** {available_payment:,.0f} 원")

    # 신규 대출 월 상환액
    new_monthly = calculate_monthly_payment(desired_loan, desired_rate, desired_years)
    st.write(f"**신규 대출 월 상환액:** {new_monthly:,.0f} 원")

    # LTV 한도
    ltv_limit = home_price * ltv
    st.write(f"### 🔒 LTV 한도 (시세×{ltv*100:.0f}%): {ltv_limit:,.0f} 원")

    # 최대 실행 가능 대출 금액
    max_by_dsr = calculate_max_loan_from_payment(available_payment, desired_rate, desired_years)
    final_loan_amount = min(max_by_dsr, ltv_limit)
    final_monthly = calculate_monthly_payment(final_loan_amount, desired_rate, desired_years)

    st.markdown("---")
    st.subheader("📊 결과 요약")
    st.write(f"- 총 DSR 비율: **{(total_existing_monthly*12)/annual_income*100:.2f}%**")
    st.write(f"- DSR 기준 최대 대출: **{max_by_dsr:,.0f} 원**")
    st.write(f"- LTV 기준 최대 대출: **{ltv_limit:,.0f} 원**")

    if desired_loan <= final_loan_amount:
        st.success(f"🎉 신규 대출 실행 가능합니다! (월 상환금: {new_monthly:,.0f}원)")
    else:
        st.error("🚫 신규 대출 실행이 어렵습니다. 조건을 조정해보세요.")
        st.info(f"💡 현재 조건으로는 **{final_loan_amount:,.0f}원**까지 대출 가능하며, 예상 월 상환금은 **{final_monthly:,.0f}원**입니다.")

# Footer
st.markdown("---")
st.caption("개발자: kim6326 | Streamlit 기반 개인용 도구")
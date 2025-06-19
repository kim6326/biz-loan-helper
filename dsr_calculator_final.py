
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

st.set_page_config(page_title="DSR 기반 대출 계산기", layout="centered")
st.title("💸 DSR 기반 대출 가능 계산기")

# 1. 연소득 입력
annual_income = st.number_input("① 연소득 (원)", min_value=0, step=1000000)

# 2. 생애최초 여부
is_first_home = st.checkbox("생애최초 주택 구입자입니까?")

# 3. 지역 선택 및 시세 입력
region_options = {"서울": 0.70, "경기": 0.65, "부산": 0.60, "기타": 0.60}
region = st.selectbox("② 지역 선택", list(region_options.keys()))
apt_price = st.number_input("③ 아파트 시세 (원)", min_value=0, step=10000000)

# 4. LTV 비율 자동/수동 선택
ltv_type = st.radio("LTV 비율 설정", ["자동", "수동"])
if ltv_type == "자동":
    base_ltv = region_options.get(region, 0.6)
    if is_first_home:
        ltv = min(0.8, base_ltv + 0.1)
    else:
        ltv = base_ltv
else:
    ltv = st.slider("직접 설정한 LTV 비율 (%)", min_value=10, max_value=90, value=60) / 100

# 5. 기존 대출 입력
st.subheader("④ 기존 대출 목록")
num_loans = st.number_input("기존 대출 수", min_value=0, max_value=10, value=0)
existing_loans = []
total_existing_dsr = 0
total_existing_monthly = 0

for i in range(num_loans):
    st.markdown(f"**📌 기존 대출 {i+1}**")
    amount = st.number_input(f"금액 (원)", key=f"amount_{i}", min_value=0)
    rate = st.number_input(f"금리 (%)", key=f"rate_{i}", min_value=0.0)
    years = st.number_input(f"기간 (년)", key=f"years_{i}", min_value=1)

    monthly = calculate_monthly_payment(amount, rate, years)
    yearly = monthly * 12
    dsr_percent = yearly / annual_income * 100 if annual_income > 0 else 0

    st.write(f"→ 월 상환액: **{monthly:,.0f}원**, 연간: {yearly:,.0f}원, DSR 기여도: {dsr_percent:.2f}%")

    existing_loans.append({"monthly": monthly, "dsr": dsr_percent})
    total_existing_monthly += monthly
    total_existing_dsr += dsr_percent

# 6. 신규 대출 조건
st.subheader("⑤ 신규 대출 조건")
new_amount = st.number_input("신규 대출 금액 (원)", min_value=0)
new_rate = st.number_input("신규 대출 금리 (%)", min_value=0.0)
new_years = st.number_input("신규 대출 기간 (년)", min_value=1)

new_monthly = calculate_monthly_payment(new_amount, new_rate, new_years)
new_yearly = new_monthly * 12
new_dsr_percent = new_yearly / annual_income * 100 if annual_income > 0 else 0

st.write(f"→ 신규 월 상환액: **{new_monthly:,.0f}원**, 연간: {new_yearly:,.0f}원, DSR 기여도: {new_dsr_percent:.2f}%")

# 총합 계산
total_dsr = total_existing_dsr + new_dsr_percent
dsr_limit = 40  # 기준 40%
ltv_limit = apt_price * ltv

st.markdown("---")
st.subheader("📊 결과 요약")
st.write(f"✅ 총 DSR 비율: **{total_dsr:.2f}%** / 기준 {dsr_limit}%")
st.write(f"✅ 아파트 시세: {apt_price:,.0f}원 / 적용 LTV: {ltv*100:.0f}%")
st.write(f"✅ 최대 대출 가능액(LTV 기준): **{ltv_limit:,.0f} 원**")

# 실행 가능 여부
ok = True
if total_dsr > dsr_limit:
    st.error(f"❌ DSR 초과로 불가능 ({total_dsr:.2f}%)")
    ok = False
if new_amount > ltv_limit:
    st.error(f"❌ LTV 초과로 불가능 (요청액 {new_amount:,.0f} > 최대 {ltv_limit:,.0f})")
    ok = False
if ok:
    st.success("✅ 신규 대출 실행 가능!")

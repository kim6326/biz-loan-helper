import streamlit as st
import re

# ✅ 페이지 설정
st.set_page_config(
    page_title="DSR 담보계산기",
    page_icon="🏦",
    layout="centered"  # 모바일 반응형
)

# 👉 자리수 콤마 표시 입력 함수
def comma_number_input(label, key, value="0"):
    user_input = st.text_input(label, value=value, key=key)
    digits_only = re.sub(r'[^0-9]', '', user_input)
    formatted = f"{int(digits_only):,}" if digits_only else ""
    st.markdown(f"<div style='color:gray; font-size:0.9em;'>입력값: {formatted}</div>", unsafe_allow_html=True)
    return int(digits_only) if digits_only else 0

# 👉 원리금 균등상환 월 납입금 계산
def calculate_monthly_payment(principal, annual_rate, years):
    if years <= 0:
        return 0
    monthly_rate = annual_rate / 100 / 12
    months = years * 12
    if monthly_rate == 0:
        return principal / months
    return principal * (monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)

# 지역별 기본 LTV
LTV_MAP = {
    "서울": 0.70,
    "경기": 0.65,
    "부산": 0.60,
    "기타": 0.60,
}

# 🔷 제목
st.title("🏦 DSR 담보계산기")

# 1. 연소득
annual_income = comma_number_input("연소득을 입력하세요", key="annual_income", value="")

# 2. 지역, 생애최초 여부, 수동입력 여부
region = st.selectbox("지역을 선택하세요", list(LTV_MAP.keys()))
first_home = st.checkbox("✅ 생애최초 주택 구입 여부")
use_custom_ltv = st.checkbox("📌 LTV 수동 입력")

# 3. LTV 계산
if use_custom_ltv:
    ltv_ratio = st.number_input("직접 입력한 LTV 비율 (%)", min_value=0.0, max_value=100.0, value=70.0, step=0.1) / 100
elif first_home:
    ltv_ratio = 0.7  # 생애최초 LTV 고정
else:
    ltv_ratio = LTV_MAP.get(region, 0.6)

# 4. 아파트 시세
apt_price = comma_number_input("아파트 시세 (KB 시세 기준)", key="apt_price")
if apt_price:
    st.markdown(f"<div style='color:gray; font-size:0.9em;'>입력된 아파트 시세: {apt_price:,} 원</div>", unsafe_allow_html=True)

# 5. 기존 대출 내역
st.subheader("📌 기존 대출 내역 입력")
existing_loans = []
num_loans = st.number_input("기존 대출 항목 수", min_value=0, max_value=10, value=0)

for i in range(num_loans):
    st.markdown(f"**대출 {i+1}**")
    amount = comma_number_input(f"대출 {i+1} 금액", key=f"amount_{i}")
    rate = st.number_input(f"대출 {i+1} 연이자율 (%)", min_value=0.0, format="%.2f", key=f"rate_{i}")
    years = st.number_input(f"대출 {i+1} 기간 (년)", min_value=0, key=f"years_{i}")
    existing_loans.append({"amount": amount, "rate": rate, "years": years})

# 6. 신규 대출 희망 조건
st.subheader("📌 신규 대출 희망 조건")
new_loan_amount = comma_number_input("희망 신규 대출 금액", key="new_loan")
new_loan_rate = st.number_input("희망 신규 대출 연이자율 (%)", min_value=0.0, format="%.2f")
new_loan_years = st.number_input("희망 신규 대출 기간 (년)", min_value=0)

# ✅ DSR 비율
DSR_RATIO = 0.4

# 👉 계산하기 버튼
if st.button("📊 계산하기"):
    total_existing_monthly = 0
    st.write("### ✅ 기존 대출 월 상환액")
    for idx, loan in enumerate(existing_loans):
        monthly = calculate_monthly_payment(loan["amount"], loan["rate"], loan["years"])
        st.write(f"대출 {idx+1}: {monthly:,.0f} 원")
        total_existing_monthly += monthly

    st.write(f"**총 기존 대출 월 상환액: {total_existing_monthly:,.0f} 원**")
    dsr_limit = (annual_income / 12) * DSR_RATIO
    st.write(f"DSR 한도 (연소득 × 40% ÷ 12개월): {dsr_limit:,.0f} 원")

    available_payment = dsr_limit - total_existing_monthly
    st.write(f"💡 신규 대출에 사용 가능한 월 상환액: {available_payment:,.0f} 원")

    ltv_limit_raw = apt_price * ltv_ratio
    ltv_limit = min(ltv_limit_raw, 600_000_000 if first_home else ltv_limit_raw)
    st.write(f"📌 LTV 기준 최대 대출 가능액: {ltv_limit:,.0f} 원")
    if first_home:
        st.caption(f"(생애최초: 최대 한도 6억 원 적용됨)")

    new_monthly_payment = calculate_monthly_payment(new_loan_amount, new_loan_rate, new_loan_years)
    st.write(f"신규 대출 월 상환액: {new_monthly_payment:,.0f} 원")

    if new_loan_amount <= ltv_limit and new_monthly_payment <= available_payment:
        st.success("✅ 신규 대출 실행 가능!")
    else:
        st.error("❌ 신규 대출 실행 불가!")

# 🔍 최대 대출 가능 금액 계산기
st.subheader("💰 신규 대출 최대 가능 금액 계산기")
calc_rate = st.number_input("계산용 연이자율 (%)", value=4.7, key="calc_rate")
calc_years = st.number_input("계산용 대출 기간 (년)", value=30, key="calc_years")

if st.button("🧮 최대 대출 가능 금액 계산"):
    total_existing_monthly = sum(
        calculate_monthly_payment(loan["amount"], loan["rate"], loan["years"]) for loan in existing_loans
    )
    dsr_limit = (annual_income / 12) * DSR_RATIO
    available_payment = dsr_limit - total_existing_monthly

    monthly_rate = calc_rate / 100 / 12
    months = calc_years * 12
    adjusted_payment = max(0, available_payment)

    if monthly_rate > 0:
        max_loan = adjusted_payment * ((1 + monthly_rate) ** months - 1) / (monthly_rate * (1 + monthly_rate) ** months)
    else:
        max_loan = adjusted_payment * months

    ltv_max = apt_price * ltv_ratio
    final_max = min(max_loan, 600_000_000 if first_home else ltv_max)

    if final_max <= 0:
        st.error("❌ 현재 조건에서는 추가 대출이 불가능합니다.")
    else:
        st.success(f"📌 최대 대출 가능 금액: {final_max:,.0f} 원 ({calc_years}년, 연 {calc_rate}% 기준)")
        st.info(f"💡 계산상 최대 가능액: {max_loan:,.0f} 원")
        st.info(f"📊 LTV 한도 적용값: {ltv_max:,.0f} 원")
        st.info(f"🏠 아파트 시세: {apt_price:,.0f} 원")

import streamlit as st
import re

# 1) 페이지 설정 (모바일·데스크탑 대응)
st.set_page_config(
    page_title="DSR 담보계산기",
    page_icon="🏦",
    layout="centered"
)

# 2) 자리수 콤마 표시 입력 함수
def comma_number_input(label, key, value="0"):
    user_input = st.text_input(label, value=value, key=key)
    digits = re.sub(r'[^0-9]', '', user_input)
    formatted = f"{int(digits):,}" if digits else ""
    st.markdown(
        f"<div style='color:gray; font-size:0.9em;'>입력값: {formatted}</div>",
        unsafe_allow_html=True
    )
    return int(digits) if digits else 0

# 3) 원리금 균등상환 월 상환액 계산 함수
def calculate_monthly_payment(principal, annual_rate, years):
    if years <= 0:
        return 0
    mr = annual_rate / 100 / 12
    n = years * 12
    if mr == 0:
        return principal / n
    return principal * mr * (1 + mr)**n / ((1 + mr)**n - 1)

# 4) 스트레스 DSR 배율 계산 함수
def get_stress_multiplier(loan_type, fixed_years, total_years, cycle_level=None):
    if loan_type == "고정형":
        return 1.0
    if loan_type == "변동형":
        return 2.0
    if loan_type == "혼합형":
        if total_years > 0:
            ratio = fixed_years / total_years
            if ratio >= 0.8:
                return 1.0
            if ratio >= 0.6:
                return 1.4
            if ratio >= 0.4:
                return 1.8
        return 2.0
    if loan_type == "주기형" and cycle_level:
        return {"1단계": 1.4, "2단계": 1.3, "3단계": 1.2}[cycle_level]
    return 1.0

# 5) 지역별 기본 LTV 맵
LTV_MAP = {"서울": 0.7, "경기": 0.65, "부산": 0.6, "기타": 0.6}

st.title("🏦 DSR 담보계산기 (최종 통합본)")

# 6) 연소득 입력
annual_income = comma_number_input("연소득을 입력하세요", key="annual_income")

# 7) 지역 / 생애최초 / LTV 수동입력
region = st.selectbox("지역을 선택하세요", list(LTV_MAP.keys()))
first_home = st.checkbox("생애최초 주택 구입 여부")
use_custom_ltv = st.checkbox("LTV 수동 입력")

if use_custom_ltv:
    ltv_ratio = st.number_input(
        "직접 입력할 LTV 비율 (%)",
        min_value=0.0, max_value=100.0, value=70.0, step=0.1
    ) / 100
elif first_home:
    ltv_ratio = 0.7
else:
    ltv_ratio = LTV_MAP[region]

# 8) 아파트 시세 입력
apt_price = comma_number_input("아파트 시세 (KB 기준)", key="apt_price")
st.markdown(f"▶ 입력 시세: {apt_price:,} 원  |  LTV: {ltv_ratio*100:.1f}%")

# 9) 기존 대출 내역 입력
st.subheader("기존 대출 내역")
existing_loans = []
num_loans = st.number_input("기존 대출 건수", min_value=0, max_value=10, value=0)
for i in range(num_loans):
    st.markdown(f"**대출 {i+1}**")
    amt = comma_number_input(f"대출 {i+1} 금액", key=f"amt_{i}")
    rate = st.number_input(f"대출 {i+1} 금리 (%)", key=f"rate_{i}", format="%.2f")
    yrs = st.number_input(f"대출 {i+1} 기간 (년)", key=f"yrs_{i}", min_value=1, value=1)
    existing_loans.append({"amount": amt, "rate": rate, "years": yrs})

# 10) 신규 대출 조건 입력
st.subheader("신규 대출 조건")
loan_type = st.selectbox("대출 유형 선택", ["고정형", "혼합형", "변동형", "주기형"])
fixed_years = 0
if loan_type == "혼합형":
    fixed_years = st.number_input("↳ 고정금리 적용 기간 (년)", min_value=0, value=5)
total_years = st.number_input("↳ 총 대출 기간 (년)", min_value=1, value=30)

cycle_level = None
if loan_type == "주기형":
    cycle_months = st.number_input("↳ 금리 리셋 주기 (개월)", min_value=1, value=12)
    if cycle_months >= 12:
        cycle_level = "1단계"
    elif cycle_months >= 6:
        cycle_level = "2단계"
    else:
        cycle_level = "3단계"
    mult_preview = get_stress_multiplier(loan_type, fixed_years, total_years, cycle_level)
    st.info(f"▶ 주기형 {cycle_months}개월 → {cycle_level}, 배율 {mult_preview:.1f}배")

new_rate = st.number_input("신규 대출 금리 (%)", min_value=0.0, format="%.2f", value=4.7)
new_amount = comma_number_input("신규 대출 금액", key="new_amount")

# 11) 계산하기
DSR_RATIO = 0.4
if st.button("계산하기"):
    exist_mon = sum(
        calculate_monthly_payment(l["amount"], l["rate"], l["years"])
        for l in existing_loans
    )
    dsr_limit = (annual_income / 12) * DSR_RATIO
    available = dsr_limit - exist_mon

    mult = get_stress_multiplier(loan_type, fixed_years, total_years, cycle_level)
    stress_rate = new_rate * mult
    new_mon = calculate_monthly_payment(new_amount, stress_rate, total_years)

    ltv_cap = apt_price * ltv_ratio
    if first_home:
        ltv_cap = min(ltv_cap, 600_000_000)

    st.write(f"▶ 기존 월 상환액: {exist_mon:,.0f} 원")
    st.write(f"▶ DSR 월 한도: {dsr_limit:,.0f} 원 (40%)")
    st.write(f"▶ 여유 상환액: {available:,.0f} 원")
    st.write(f"▶ 스트레스 금리: {stress_rate:.2f}% (배율 {mult:.1f}배)")
    st.write(f"▶ 신규 월 상환액: {new_mon:,.0f} 원")
    st.write(f"▶ LTV 한도: {ltv_ratio*100:.1f}% → {ltv_cap:,.0f} 원")

    if new_amount <= ltv_cap and new_mon <= available:
        st.success("✅ 신규 대출 실행 가능!")
    else:
        st.error("❌ 신규 대출 실행 불가: DSR 또는 LTV 초과")

# 12) 최대 대출 가능금액 역산
st.subheader("최대 대출 가능금액 계산기")
calc_rate = st.number_input("계산용 금리 (%)", value=4.7, format="%.2f", key="calc_rate")
calc_years = st.number_input("계산용 기간 (년)", value=30, key="calc_years")
if st.button("최대 계산"):
    exist_mon = sum(
        calculate_monthly_payment(l["amount"], l["rate"], l["years"])
        for l in existing_loans
    )
    dsr_limit = (annual_income / 12) * DSR_RATIO
    available = dsr_limit - exist_mon
    mr = (calc_rate * mult) / 100 / 12
    n = calc_years * 12
    max_loan = (available * ((1+mr)**n - 1) / (mr*(1+mr)**n)) if mr > 0 else available * n

    cap = apt_price * ltv_ratio
    if first_home:
        cap = min(cap, 600_000_000)
    final = min(max_loan, cap)

    if final > 0:
        st.success(f"📌 최대 대출 가능 금액: {final:,.0f} 원")
    else:
        st.error("❌ 추가 대출 불가")

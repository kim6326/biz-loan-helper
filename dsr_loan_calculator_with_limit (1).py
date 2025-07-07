import streamlit as st
import re
from datetime import datetime

st.set_page_config(
    page_title="대출 계산기 통합 앱",
    page_icon="🏦",
    layout="centered"
)

def comma_number_input(label, key, value="0"):
    user_input = st.text_input(label, value=value, key=key)
    digits = re.sub(r'[^0-9]', '', user_input)
    formatted = f"{int(digits):,}" if digits else ""
    st.markdown(f"<div style='color:gray; font-size:0.9em;'>입력값: {formatted}</div>", unsafe_allow_html=True)
    return int(digits) if digits else 0

def calculate_monthly_payment(principal, annual_rate, years):
    if years <= 0: return 0
    mr = annual_rate / 100 / 12
    n = years * 12
    if mr == 0: return principal / n
    return principal * mr * (1 + mr)**n / ((1 + mr)**n - 1)

def get_stress_multiplier(loan_type, fixed_years, total_years, cycle_level=None):
    if loan_type == "고정형": return 1.0
    if loan_type == "변동형": return 2.0
    if loan_type == "혼합형":
        if total_years > 0:
            ratio = fixed_years / total_years
            if ratio >= 0.8: return 1.0
            if ratio >= 0.6: return 1.4
            if ratio >= 0.4: return 1.8
        return 2.0
    if loan_type == "주기형" and cycle_level:
        return {"1단계":1.4,"2단계":1.3,"3단계":1.2}[cycle_level]
    return 1.0

LTV_MAP = {"서울":0.7,"경기":0.7,"인천":0.7,"부산":0.6,"기타":0.6}

page = st.sidebar.selectbox("계산기 선택", ["DSR 담보계산기", "전세대출 계산기"])

if page == "DSR 담보계산기":
    st.title("🏦 DSR 담보계산기 (스트레스 감면 포함)")

    annual_income = comma_number_input("연소득을 입력하세요", "annual_income")
    region = st.selectbox("지역을 선택하세요", list(LTV_MAP.keys()))
    first_home = st.checkbox("생애최초 주택 구입 여부")
    use_custom_ltv = st.checkbox("LTV 수동 입력")

    if use_custom_ltv:
        ltv_ratio = st.number_input("직접 LTV 비율 (%)", 0.0,100.0,70.0,0.1)/100
    elif first_home:
        ltv_ratio = 0.70
    else:
        ltv_ratio = LTV_MAP[region]

    apt_price = comma_number_input("아파트 시세 (KB 기준)", "apt_price")
    st.markdown(f"▶ 시세: {apt_price:,} 원  |  LTV: {ltv_ratio*100:.1f}%")

    st.subheader("기존 대출 내역")
    existing_loans = []
    num = st.number_input("기존 대출 건수", 0,10,0)
    for i in range(num):
        amt = comma_number_input(f"대출 {i+1} 금액", f"amt{i}")
        rate = st.number_input(f"대출 {i+1} 금리 (%)", key=f"rate{i}", format="%.2f")
        yrs  = st.number_input(f"대출 {i+1} 기간 (년)", key=f"yrs{i}", min_value=1, value=1)
        existing_loans.append({"amount":amt,"rate":rate,"years":yrs})

    st.subheader("신규 대출 조건")
    loan_type = st.selectbox("대출 유형", ["고정형","혼합형","변동형","주기형"])
    fixed_years = 0
    if loan_type=="혼합형":
        fixed_years = st.number_input("↳ 고정금리 적용 기간 (년)", 0,100,5)
    total_years = st.number_input("↳ 총 대출 기간 (년)", 1,100,30)

    cycle_level = None
    if loan_type=="주기형":
        cycle_mon = st.number_input("↳ 금리 리셋 주기 (개월)",1,120,12)
        if cycle_mon>=12: cycle_level="1단계"
        elif cycle_mon>=6: cycle_level="2단계"
        else: cycle_level="3단계"
        mult_preview = get_stress_multiplier(loan_type,fixed_years,total_years,cycle_level)
        st.info(f"▶ 주기형 {cycle_mon}개월 → {cycle_level}, 배율 {mult_preview:.1f}배")

    new_rate   = st.number_input("신규 금리 (%)",0.0,10.0,4.7,0.01)
    new_amount = comma_number_input("신규 대출 금액","new_amount")

    DSR_RATIO = 0.4

    if st.button("계산하기"):
        exist_mon = sum(calculate_monthly_payment(l["amount"],l["rate"],l["years"]) for l in existing_loans)
        dsr_limit = annual_income/12 * DSR_RATIO
        available = dsr_limit - exist_mon

        mult = get_stress_multiplier(loan_type,fixed_years,total_years,cycle_level)
        stress_rate = new_rate * mult

        discount = 1.5 if region in ["서울","경기","인천"] else 0.75
        adjusted_rate = stress_rate - discount

        new_mon = calculate_monthly_payment(new_amount,adjusted_rate,total_years)
        ltv_cap = min(apt_price*ltv_ratio, 600_000_000 if first_home else apt_price*ltv_ratio)

        st.write(f"기존 월 상환액: {exist_mon:,.0f} 원")
        st.write(f"DSR 한도: {dsr_limit:,.0f} 원")
        st.write(f"여유 상환액: {available:,.0f} 원")
        st.write(f"스트레스 금리 (전): {stress_rate:.2f}%  →  (감면 후) {adjusted_rate:.2f}% (−{discount:.2f}%p)")
        st.write(f"신규 월 상환액: {new_mon:,.0f} 원")
        st.write(f"LTV 한도: {ltv_ratio*100:.1f}% → {ltv_cap:,.0f} 원")

        if new_amount<=ltv_cap and new_mon<=available:
            st.success("✅ 신규 대출 가능")
        else:
            st.error("❌ 신규 대출 불가")

    st.subheader("최대 대출 가능금액 계산기")
    calc_rate  = st.number_input("계산용 금리 (%)",0.0,10.0,4.7,0.01,key="calc_rate")
    calc_years = st.number_input("계산용 기간 (년)",1,100,30,key="calc_years")
    if st.button("최대 계산"):
        exist_mon = sum(calculate_monthly_payment(l["amount"],l["rate"],l["years"]) for l in existing_loans)
        available = annual_income/12 * DSR_RATIO - exist_mon
        mult_max = get_stress_multiplier(loan_type,fixed_years,total_years,cycle_level)
        mr = (calc_rate * mult_max)/100/12
        n  = calc_years*12
        max_loan = (available*((1+mr)**n -1)/(mr*(1+mr)**n)) if mr>0 else available*n
        cap = min(apt_price*ltv_ratio, 600_000_000 if first_home else apt_price*ltv_ratio)

        if max_loan>0:
            st.success(f"최대 가능 대출금: {min(max_loan,cap):,.0f} 원")
        else:
            st.error("추가 대출 불가")

elif page == "전세대출 계산기":
    st.title("📊 전세대출 한도 계산기")

    age = st.number_input("나이", 19, 70, 32)
    married = st.radio("결혼 여부", ["미혼", "결혼"]) == "결혼"
    income_man = comma_number_input("연소득 (만원)", "income_man", "6000")
    income = income_man * 10000
    mp = comma_number_input("아파트 시세 (원)", "mp_input", "500000000")
    je = comma_number_input("전세 보증금 (원)", "je_input", "450000000")
    ho = comma_number_input("희망 대출 금액 (원)", "ho_input", "300000000")
    rate = st.number_input("이자율 (%)", 0.0, 10.0, 3.5, 0.1)
    yrs = st.number_input("기간 (년)", 1, 30, 2)
    use_stress = st.checkbox("스트레스 금리 적용 (금리 +0.6%)")
    repay_type = "만기일시"
    effective_rate = rate + 0.6 if use_stress else rate

    if ho > 0:
        ho_monthly = calculate_monthly_payment(ho, effective_rate, yrs)
        st.markdown(f"💵 희망 대출 월 상환액: {int(ho_monthly):,}원")

    sample_amt = comma_number_input("예시 대출금액 (원)", "sample_amt", "500000000")
    example_monthly = calculate_monthly_payment(sample_amt, effective_rate, yrs)
    st.markdown(f"📌 예시 {sample_amt:,}원 월 상환액: {int(example_monthly):,}원")

   
   

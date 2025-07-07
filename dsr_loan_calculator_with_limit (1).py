import streamlit as st
import re
from datetime import datetime

st.set_page_config(
    page_title="대출 계산기 통합 앱",
    page_icon="🏦",
    layout="centered"
)

# 숫자 입력 및 콤마 출력

def comma_number_input(label, key, value="0"):
    user_input = st.text_input(label, value=value, key=key)
    digits = re.sub(r'[^0-9]', '', user_input)
    formatted = f"{int(digits):,}" if digits else ""
    st.markdown(f"<div style='color:gray; font-size:0.9em;'>입력값: {formatted}</div>", unsafe_allow_html=True)
    return int(digits) if digits else 0

# 월 상환액 계산

def calculate_monthly_payment(principal, years, rate, repay_type="원리금균등"):
    months = years * 12
    r = rate / 100 / 12
    if repay_type == "원리금균등":
        return principal / months if r == 0 else principal * r * (1 + r)**months / ((1 + r)**months - 1)
    if repay_type == "원금균등":
        p = principal / months
        return p + principal * r
    if repay_type == "만기일시":
        return principal * r
    return 0

# DSR 계산

def calculate_dsr(existing_loans, annual_income):
    total = sum(
        calculate_monthly_payment(loan['amount'], loan['period'], loan['rate'], loan['repay_type']) * 12
        for loan in existing_loans
    )
    return total / annual_income * 100 if annual_income > 0 else 0

# 상품 추천

def recommend_product(age, is_married, income, market_price, jeonse_price, hope_loan, org):
    max_possible = min(jeonse_price, market_price * 0.8)

    if age <= 34 and income <= 70000000:
        limit = min(max_possible, 200000000 if org == "HUG" else 100000000)
        prod = "청년 전세자금대출"
    elif is_married and income <= 80000000:
        limit = min(max_possible, 240000000)
        prod = "신혼부부 전세자금대출"
    else:
        limit = min(max_possible, 500000000)
        prod = "일반 전세자금대출"

    return prod, limit, hope_loan <= limit

LTV_MAP = {"서울":0.7, "경기":0.7, "인천":0.7, "부산":0.6, "기타":0.6}

# 이력 저장 초기화
if 'history' not in st.session_state:
    st.session_state.history = []

# 사이드바 메뉴
page = st.sidebar.selectbox("계산기 선택", ["전세대출 계산기", "DSR 담보대출 계산기", "내 이력"])

# 전세대출 계산기
if page == "전세대출 계산기":
    st.title("📊 전세대출 한도 계산기 with DSR")
    age = st.number_input("나이", 19, 70, 32)
    married = st.radio("결혼 여부", ["미혼", "결혼"]) == "결혼"
    income_man = comma_number_input("연소득 (만원)", "income_man", "6000")
    income = income_man * 10000
    mp = comma_number_input("아파트 시세 (원)", "mp_input", "500000000")
    je = comma_number_input("전세 보증금 (원)", "je_input", "450000000")
    ho = comma_number_input("희망 대출 금액 (원)", "ho_input", "300000000")
    org = st.selectbox("보증기관", ["HUG", "HF", "SGI"])
    rate = st.number_input("이자율 (%)", 0.0, 10.0, 3.5, 0.1)
    yrs = st.number_input("기간 (년)", 1, 30, 2)
    repay_type = "만기일시"
    use_stress = st.checkbox("스트레스 금리 적용 (금리 +0.6%)")
    effective_rate = rate + 0.6 if use_stress else rate
    if ho > 0:
        ho_monthly = calculate_monthly_payment(ho, yrs, effective_rate, repay_type)
        st.markdown(f"💵 희망 대출 월 상환액: {int(ho_monthly):,}원")
    sample_amt = comma_number_input("예시 대출금액 (원)", "sample_amt", "500000000")
    example_monthly = calculate_monthly_payment(sample_amt, yrs, effective_rate, repay_type)
    st.markdown(f"📌 예시 {sample_amt:,}원 월 상환액: {int(example_monthly):,}원")
    num = st.number_input("기존 대출 건수", 0, 10, 0)
    existing_loans = []
    for i in range(num):
        amt = comma_number_input(f"대출 {i+1} 금액", f"je_amt{i}")
        pr = st.number_input(f"기간(년)", 1, 40, 10, key=f"je_pr{i}")
        rt = st.number_input(f"이율(%)", 0.0, 10.0, 4.0, key=f"je_rt{i}")
        rp = st.selectbox(f"상환방식", ["원리금균등","원금균등","만기일시"], key=f"je_rp{i}")
        existing_loans.append({"amount": amt, "period": pr, "rate": rt, "repay_type": rp})
    if st.button("계산"):
        curr = calculate_dsr(existing_loans, income)
        est = calculate_dsr(existing_loans + [{"amount": ho, "period": yrs, "rate": effective_rate, "repay_type": repay_type}], income)
        prod, lim, ok = recommend_product(age, married, income, mp, je, ho, org)
        st.markdown(f"현재 DSR: {curr:.2f}% / 예상 DSR: {est:.2f}%")
        st.markdown(f"추천상품: {prod} / 한도: {lim:,}원 / {'가능' if ok else '불가'}")
        st.session_state.history.append({
            'type':'전세','time':datetime.now().strftime('%Y-%m-%d %H:%M'),
            'inputs':{'age':age,'income':income,'mp':mp,'je':je,'ho':ho,'rate':rate,'yrs':yrs},
            'result':{'current_dsr':curr,'estimated_dsr':est,'product':prod,'limit':lim,'approved':ok}
        })

   
    

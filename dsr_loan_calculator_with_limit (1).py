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

# --- 전세대출 계산기 함수 ---
def calculate_monthly_payment(principal, years, rate, repay_type="원리금균등"):
    months = years * 12
    r = rate / 100 / 12
    if repay_type == "원리금균등":
        if r == 0:
            return principal / months
        return principal * r * (1 + r)**months / ((1 + r)**months - 1)
    elif repay_type == "원금균등":
        p = principal / months
        return p + principal * r
    elif repay_type == "만기일시":
        return principal * r
    return 0

def calculate_dsr(existing_loans, annual_income):
    total = sum(calculate_monthly_payment(l['amount'], l['period'], l['rate'], l['repay_type']) * 12 for l in existing_loans)
    return total / annual_income * 100 if annual_income > 0 else 0

def recommend_product(age, is_married, income, market_price, hope_loan, org):
    if age <= 34 and income <= 70000000:
        prod, limit = "청년 전세자금대출", (200000000 if org == "HUG" else 100000000)
    elif is_married and income <= 80000000:
        prod, limit = "신혼부부 전세자금대출", 240000000
    else:
        prod, limit = "일반 전세자금대출", min(market_price * 0.8, 500000000)
    return prod, limit, hope_loan <= limit

# --- DSR 담보계산기 함수 ---
def get_stress_multiplier(loan_type, fixed_years, total_years, cycle_level=None):
    if loan_type == "고정형": return 1.0
    if loan_type == "변동형": return 2.0
    if loan_type == "혼합형":
        ratio = fixed_years / total_years if total_years > 0 else 0
        if ratio >= 0.8: return 1.0
        if ratio >= 0.6: return 1.4
        if ratio >= 0.4: return 1.8
        return 2.0
    if loan_type == "주기형" and cycle_level:
        return {"1단계":1.4, "2단계":1.3, "3단계":1.2}[cycle_level]
    return 1.0

LTV_MAP = {"서울":0.7, "경기":0.7, "인천":0.7, "부산":0.6, "기타":0.6}

# --- UI 시작 ---
page = st.sidebar.selectbox("계산기 선택", ["전세대출 계산기", "DSR 담보계산기"])

if page == "전세대출 계산기":
    st.title("📊 전세대출 한도 계산기 with DSR")
    # 입력 필드
    age = st.number_input("나이", 19, 70, 32)
    married = st.radio("결혼 여부", ["미혼", "결혼"]) == "결혼"
    raw_income = st.text_input("연소득 (만원)", "6000")
    try:
        income = int(raw_income.replace(',', '')) * 10000
    except:
        income = 0
        st.error("숫자만 입력하세요.")
    raw_mp = st.text_input("아파트 시세 (원)", "500000000")
    try:
        mp = int(raw_mp.replace(',', ''))
    except:
        mp = 0
        st.error("숫자만 입력하세요.")
    raw_je = st.text_input("전세 보증금 (원)", "450000000")
    try:
        je = int(raw_je.replace(',', ''))
    except:
        je = 0
        st.error("숫자만 입력하세요.")
    raw_ho = st.text_input("희망 대출 금액 (원)", "300000000")
    try:
        ho = int(raw_ho.replace(',', ''))
    except:
        ho = 0
        st.error("숫자만 입력하세요.")
    org = st.selectbox("보증기관", ["HUG", "HF", "SGI"])
    rate = st.number_input("이자율 (%)", 0.0, 10.0, 3.5, 0.1)
    yrs = st.number_input("기간 (년)", 1, 30, 2)
    num = st.number_input("기존 대출 건수", 0, 10, 0)
    el = []
    for i in range(num):
        amt = comma_number_input(f"대출 {i+1} 금액 (원)", f"a{i}")
        pr = st.number_input(f"대출 {i+1} 기간 (년)", 1, 40, 10, key=f"p{i}")
        rt = st.number_input(f"대출 {i+1} 이자율 (%)", 0.0, 10.0, 4.0, key=f"r{i}")
        rp = st.selectbox(f"상환방식 {i+1}", ["원리금균등", "원금균등", "만기일시"], key=f"rp{i}")
        el.append({"amount": amt, "period": pr, "rate": rt, "repay_type": rp})
    if st.button("계산"):        
        curr = calculate_dsr(el, income)
        est = calculate_dsr(el + [{"amount":ho, "period":yrs, "rate":rate, "repay_type":"원리금균등"}], income)
        prod, lim, ok = recommend_product(age, married, income, mp, ho, org)
        st.markdown(f"현재 DSR: {curr:.2f}% / 예상 DSR: {est:.2f}%")
        st.markdown(f"추천상품: {prod} / 한도: {lim:,}원 / 가능여부: {'가능' if ok else '불가'}")
        # 리포트 생성 및 다운로드
        report = f"전세대출 계산 보고서\n날짜: {datetime.now().strftime('%Y-%m-%d')}\n" \
                 f"나이: {age}, 결혼: {'O' if married else 'X'}\n" \
                 f"연소득: {income:,}원, 시세: {mp:,}원, 전세금: {je:,}원\n" \
                 f"희망대출: {ho:,}원, 보증기관: {org}, 금리: {rate:.2f}%, 기간: {yrs}년\n" \
                 f"현재 DSR: {curr:.2f}%, 예상 DSR: {est:.2f}%\n" \
                 f"추천상품: {prod}, 한도: {lim:,}원, 승인여부: {'가능' if ok else '불가'}"
        st.download_button("📄 보고서 다운로드", report, file_name="jeonse_report.txt", mime="text/plain")

else:
    st.title("🏦 DSR 담보계산기 (스트레스 감면 포함)")
    income2 = comma_number_input("연소득(원)", "inc2")
    region = st.selectbox("지역", list(LTV_MAP.keys()))
    fh = st.checkbox("생애최초")
    custom = st.checkbox("LTV 수동 입력")
    if custom:
        ltv = st.number_input("직접 LTV (%)", 0.0, 100.0, 70.0) / 100
    elif fh:
        ltv = 0.7
    else:
        ltv = LTV_MAP[region]
    price = comma_number_input("시세(원)", "mp2")
    st.markdown(f"시세: {price:,}원 | LTV: {ltv*100:.1f}%")
    # ... 이하 기존 담보 계산기 로직 유지 ...



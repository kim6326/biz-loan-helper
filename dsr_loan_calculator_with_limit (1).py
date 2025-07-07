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
    st.markdown(
        f"<div style='color:gray; font-size:0.9em;'>입력값: {formatted}</div>",
        unsafe_allow_html=True
    )
    return int(digits) if digits else 0

# 월 상환액 계산

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

# DSR 계산

def calculate_dsr(existing_loans, annual_income):
    total = sum(
        calculate_monthly_payment(loan['amount'], loan['period'], loan['rate'], loan['repay_type']) * 12
        for loan in existing_loans
    )
    return total / annual_income * 100 if annual_income > 0 else 0

# 상품 추천

def recommend_product(age, is_married, income, market_price, hope_loan, org):
    if age <= 34 and income <= 70000000:
        prod, limit = "청년 전세자금대출", (200000000 if org == "HUG" else 100000000)
    elif is_married and income <= 80000000:
        prod, limit = "신혼부부 전세자금대출", 240000000
    else:
        prod, limit = "일반 전세자금대출", min(market_price * 0.8, 500000000)
    return prod, limit, hope_loan <= limit

# 스트레스 배율 계산 (전세용)

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

# 이력 저장 초기화

if 'history' not in st.session_state:
    st.session_state.history = []

# 사이드바 메뉴

page = st.sidebar.selectbox("계산기 선택", ["전세대출 계산기", "DSR 담보계산기", "내 이력"])

# 전세대출 계산기 화면

if page == "전세대출 계산기":
    st.title("📊 전세대출 한도 계산기 with DSR")

    # 사용자 입력
    age = st.number_input("나이", 19, 70, 32)
    married = st.radio("결혼 여부", ["미혼", "결혼"]) == "결혼"
    raw_income = st.text_input("연소득 (만원)", "6000")
    try:
        income = int(raw_income.replace(',', '')) * 10000
    except:
        income = 0
        st.error("연소득은 숫자로 입력해주세요.")
    raw_mp = st.text_input("아파트 시세 (원)", "500000000")
    try:
        mp = int(raw_mp.replace(',', ''))
    except:
        mp = 0
        st.error("시세는 숫자로 입력해주세요.")
    raw_je = st.text_input("전세 보증금 (원)", "450000000")
    try:
        je = int(raw_je.replace(',', ''))
    except:
        je = 0
        st.error("전세금은 숫자로 입력해주세요.")
    raw_ho = st.text_input("희망 대출 금액 (원)", "300000000")
    try:
        ho = int(raw_ho.replace(',', ''))
    except:
        ho = 0
        st.error("대출 금액은 숫자로 입력해주세요.")
    org = st.selectbox("보증기관", ["HUG", "HF", "SGI"])
    rate = st.number_input("이자율 (%)", 0.0, 10.0, 3.5, 0.1)
    yrs = st.number_input("기간 (년)", 1, 30, 2)

    # 스트레스 금리 옵션
    use_stress = st.checkbox("📈 스트레스 금리 적용 (+0.6%)")
    effective_rate = rate + 0.6 if use_stress else rate
    st.markdown(f"고객 안내용 금리: **{rate:.2f}%**")
    if use_stress:
        st.markdown(f"내부 DSR 계산용 금리: **{effective_rate:.2f}%**")

    # 생활안정자금 섹션
    st.markdown("---")
    st.markdown("### 💼 생활안정자금 여부")
    want_life = st.checkbox("생활안정자금 추가 신청")
    life_amount = 0
    if want_life:
        st.info("생활안정자금은 세입자 본인 계좌로 입금되며, 집주인 동의는 필요하지 않습니다.")
        total_limit = min(mp * 0.8, 500000000)
        remaining = max(0, total_limit - ho)
        st.markdown(f"💡 생활안정자금 가능 한도: **{remaining:,}원**")
        life_years = st.number_input("생활안정자금 기간 (년)", 1, 10, 3)
        life_rate = st.number_input("생활안정자금 금리 (%)", 0.0, 10.0, 4.13)
        life_amount = st.number_input("신청 금액 (원)", 0, remaining, step=1000000)
        if life_amount > 0:
            life_monthly = calculate_monthly_payment(life_amount, life_years, life_rate)
            st.markdown(f"📆 생활안정자금 월 예상 상환액: **{int(life_monthly):,}원**")

    # 기존 대출 내역 입력
    num = st.number_input("기존 대출 건수", 0, 10, 0)
    existing_loans = []
    for i in range(num):
        amt = comma_number_input(f"대출 {i+1} 금액 (원)", f"je_loan_amt{i}")
        pr = st.number_input(f"대출 {i+1} 기간 (년)", 1, 40, 10, key=f"je_loan_pr{i}")
        rt = st.number_input(f"대출 {i+1} 이자율 (%)", 0.0, 10.0, 4.0, key=f"je_loan_rt{i}")
        rp = st.selectbox(f"상환방식 {i+1}", ["원리금균등", "원금균등", "만기일시"], key=f"je_loan_rp{i}")
        existing_loans.append({"amount": amt, "period": pr, "rate": rt, "repay_type": rp})

    # 계산 버튼
    if st.button("계산"):        
        curr = calculate_dsr(existing_loans, income)
        est = calculate_dsr(
            existing_loans + [{"amount": ho, "period": yrs, "rate": effective_rate, "repay_type": "원리금균등"}],
            income
        )
        prod, lim, ok = recommend_product(age, married, income, mp, ho, org)
        st.markdown(f"현재 DSR: **{curr:.2f}%** / 예상 DSR: **{est:.2f}%**")
        st.markdown(f"추천상품: **{prod}** / 한도: **{lim:,}원** / 가능여부: **{'가능' if ok else '불가'}**")
        # 이력 저장
        st.session_state.history.append({
            'type': '전세',
            'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'inputs': {'age': age, 'income': income, 'market_price': mp,
                       'jeonse_deposit': je, 'hope_loan': ho, 'org': org,
                       'rate': rate, 'years': yrs, 'stress': use_stress,
                       'life_amount': life_amount},
            'result': {'current_dsr': curr, 'estimated_dsr': est,
                       'product': prod, 'limit': lim, 'approved': ok}
        })

# DSR 담보계산기 및 내 이력 페이지는 이하 생략...

      
 
 

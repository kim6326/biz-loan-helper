import streamlit as st
import re
from datetime import datetime

st.set_page_config(
    page_title="대출 계산기 통합 앱",
    page_icon="🏦",
    layout="centered"
)

# ─── LTV 및 DSR 비율 설정 ──────────────────────────────────
LTV_MAP = {
    "서울": 0.7,
    "경기": 0.7,
    "인천": 0.7,
    "부산": 0.6,
    "기타": 0.6
}
DSR_RATIO = 0.4
# ────────────────────────────────────────────────────────

# 숫자 입력 및 콤마 출력 함수
def comma_number_input(label, key, value="0"):
    user_input = st.text_input(label, value=value, key=key)
    digits = re.sub(r'[^0-9]', '', user_input)
    formatted = f"{int(digits):,}" if digits else ""
    st.markdown(
        f"<div style='color:gray; font-size:0.9em;'>입력값: {formatted}</div>", unsafe_allow_html=True
    )
    return int(digits) if digits else 0

# 월 상환액 계산 함수
def calculate_monthly_payment(principal, rate, years, repay_type="원리금균등"):
    months = years * 12
    mr = rate / 100 / 12
    if repay_type == "원리금균등":
        return principal / months if mr == 0 else principal * mr * (1 + mr)**months / ((1 + mr)**months - 1)
    if repay_type == "원금균등":
        p = principal / months
        return p + principal * mr
    if repay_type == "만기일시":
        return principal * mr
    return 0

# DSR 계산 함수
def calculate_dsr(existing_loans, annual_income):
    total = sum(
        calculate_monthly_payment(
            loan['amount'], loan['rate'], loan['years'], loan['repay_type']
        ) * 12 for loan in existing_loans
    )
    return (total / annual_income * 100) if annual_income > 0 else 0

# 전세대출 상품 추천 함수
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
    return prod, limit, (hope_loan <= limit)

# 스트레스 배율 함수
def get_stress_multiplier(loan_type, fixed_years, total_years, cycle_level=None):
    if loan_type == "고정형":
        return 1.0
    if loan_type == "변동형":
        return 2.0
    if loan_type == "혼합형":
        if total_years > 0:
            ratio = fixed_years / total_years
            if ratio >= 0.8: return 1.0
            if ratio >= 0.6: return 1.4
            if ratio >= 0.4: return 1.8
        return 2.0
    if loan_type == "주기형" and cycle_level:
        return {"1단계":1.4, "2단계":1.3, "3단계":1.2}[cycle_level]
    return 1.0

# 세션 이력 초기화
if 'history' not in st.session_state:
    st.session_state.history = []

# 사이드바 메뉴
page = st.sidebar.selectbox(
    "계산기 선택",
    ["전세대출 계산기", "DSR 담보대출 계산기", "내 이력"]
)

# 전세대출 계산기
if page == "전세대출 계산기":
    st.title("📊 전세대출 한도 계산기")
    age = st.number_input("나이", 19, 70, 32)
    is_married = st.radio("결혼 여부", ["미혼", "결혼"]) == "결혼"
    income_man = comma_number_input("연소득 (만원)", "inc", "6000")
    income = income_man * 10000
    market_price = comma_number_input("시세 (원)", "mp", "500000000")
    jeonse_price = comma_number_input("전세 보증금 (원)", "je", "450000000")
    hope_loan = comma_number_input("희망 대출 (원)", "hp", "300000000")
    org = st.selectbox("보증기관", ["HUG", "HF", "SGI"])
    rate = st.number_input("이자율 (%)", 0.0, 10.0, 3.5, 0.1)
    years = st.number_input("기간 (년)", 1, 30, 2)
    use_stress = st.checkbox("스트레스 금리 적용 (+0.6%))")
    effective_rate = rate + 0.6 if use_stress else rate

    if st.button("계산전세"):
        prod, limit, approved = recommend_product(age, is_married, income, market_price, jeonse_price, hope_loan, org)
        st.markdown(f"추천상품: {prod}")
        st.markdown(f"한도: {limit:,}원 / {'가능' if approved else '불가'}")
        st.session_state.history.append({'type':'전세','time':datetime.now().strftime('%Y-%m-%d %H:%M'),'result':{'prod':prod,'limit':limit,'approved':approved}})

# DSR 담보대출 계산기
elif page == "DSR 담보대출 계산기":
    st.title("🏦 DSR 담보대출 계산기 (스트레스 감면 포함)")
    annual_income = comma_number_input("연소득 (만원)", "dsr_inc", "6000") * 10000
    region = st.selectbox("지역", list(LTV_MAP.keys()))
    first_home = st.checkbox("생애최초 구매 여부")
    custom_ltv = st.checkbox("직접 LTV 입력")
    if custom_ltv:
        ltv_ratio = st.number_input("LTV (%)", 0.0, 100.0, 70.0, 0.1) / 100
    elif first_home:
        ltv_ratio = 0.7
    else:
        ltv_ratio = LTV_MAP[region]
    property_price = comma_number_input("시세 (원)", "pp", "500000000")

    st.subheader("기존 대출 내역")
    existing_loans = []
    cnt_loan = st.number_input("기존 대출 건수", 0, 10, 0)
    for i in range(cnt_loan):
        amt = comma_number_input(f"대출 {i+1} 금액(원)", f"amt{i}")
        yr = st.number_input(f"기간(년) {i+1}", 1, 40, 10, key=f"yr{i}")
        rt = st.number_input(f"이율(%) {i+1}", 0.0, 10.0, 4.0, key=f"rt{i}")
        repay = st.selectbox(f"상환방식 {i+1}", ["원리금균등", "원금균등", "만기일시"], key=f"rep{i}")
        existing_loans.append({'amount': amt, 'rate': rt, 'years': yr, 'repay_type': repay})

    st.subheader("신규 대출 조건")
    loan_type = st.selectbox("대출 유형", ["고정형", "혼합형", "변동형", "주기형"])
    fixed_years = 0
    total_years = st.number_input("총 기간(년)", 1, 100, 30)
    if loan_type == "혼합형":
        fixed_years = st.number_input("고정금리 기간(년)", 0, total_years, 5)
    cycle_level = None
    if loan_type == "주기형":
        cm = st.number_input("리셋 주기(개월)", 1, 120, 12)
        cycle_level = "1단계" if cm >= 12 else ("2단계" if cm >= 6 else "3단계")
        st.info(f"주기형 {cm}개월→{cycle_level}")
    new_rate = st.number_input("신규 금리(%)", 0.0, 10.0, 4.7)
    new_amt = comma_number_input("신규 대출 금액(원)", "na", "300000000")

    if st.button("계산담보"):
        exist_mon = sum(calculate_monthly_payment(l['amount'], l['rate'], l['years'], l['repay_type']) for l in existing_loans)
        dsr_lim = annual_income / 12 * DSR_RATIO
        avail = dsr_lim - exist_mon
        mult = get_stress_multiplier(loan_type, fixed_years, total_years, cycle_level)
        stress = new_rate * mult
        disc = 1.5 if region in ["서울", "경기", "인천"] else 0.75
        adj = stress - disc
        new_mon = calculate_monthly_payment(new_amt, adj, total_years, "만기일시")
        cap = min(property_price * ltv_ratio, 600_000_000 if first_home else property_price * ltv_ratio)
        st.write(f"기존 월 상환:{exist_mon:,.0f}원/DSR한도:{dsr_lim:,.0f}원/여유:{avail:,.0f}원")
        st.write(f"신규 월 상환:{new_mon:,.0f}원/LTV한도:{cap:,.0f}원")
                        # 최대 신규 대출 가능금액 계산 (DSR 기준)
        # 조정금리(adj)에 기반해 DSR 한도를 월 상환액 식으로 역산
        if adj > 0:
            max_dsr = avail * 12 / (adj / 100)
        else:
            max_dsr = cap
        max_loan = min(max_dsr, cap)
        st.info(f"✨최대 대출 가능금액:{int(max_loan):,}원")
        if new_amt <= cap and new_mon <= avail:
            st.success("✅ 가능")
            approved = True
        else:
            st.error("❌ 불가")
            approved = False
        st.session_state.history.append({'type': '담보', 'time': datetime.now().strftime('%Y-%m-%d %H:%M'), 'result': {'approved': approved, 'max_loan': max_loan}})

# 내 계산 이력
else:
    st.title("⏳ 내 계산 이력")
    if st.session_state.history:
        for r in st.session_state.history:
            st.markdown(f"**[{r['time']}] {r['type']}**")
            st.json(r['result'])
    else:
        st.info("아직 계산 이력이 없습니다.")

 
     

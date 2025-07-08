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

# 숫자 입력 및 콤마 출력
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

# 전세대출 상품 추천 함수 (수정된 한도 로직)
def recommend_product(age, is_married, income, market_price, jeonse_price, hope_loan, org):
    # 전세보증금과 시세의 80% 중 작은 값을 최대 한도로 설정
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
        ho_mon = calculate_monthly_payment(ho, effective_rate, yrs, repay_type)
        st.markdown(f"💵 희망 대출 월 상환액: {int(ho_mon):,}원")

    sample_amt = comma_number_input("예시 대출금액 (원)", "sample_amt", "500000000")
    example_mon = calculate_monthly_payment(sample_amt, effective_rate, yrs, repay_type)
    st.markdown(f"📌 예시 {sample_amt:,}원 월 상환액: {int(example_mon):,}원")

    st.subheader("기존 대출 내역")
    existing_loans = []
    cnt = st.number_input("기존 대출 건수", 0, 10, 0)
    for i in range(cnt):
        amt = comma_number_input(f"대출 {i+1} 금액", f"je_amt{i}")
        pr = st.number_input(f"기간(년)", 1, 40, 10, key=f"je_pr{i}")
        rt = st.number_input(f"이율(%)", 0.0, 10.0, 4.0, key=f"je_rt{i}")
        rp = st.selectbox(f"상환방식", ["원리금균등", "원금균등", "만기일시"], key=f"je_rp{i}")
        existing_loans.append({"amount": amt, "rate": rt, "years": pr, "repay_type": rp})

    if st.button("계산"):
        curr = calculate_dsr(existing_loans, income)
        est = calculate_dsr(
            existing_loans + [{"amount": ho, "rate": effective_rate, "years": yrs, "repay_type": repay_type}],
            income
        )
        prod, lim, ok = recommend_product(age, married, income, mp, je, ho, org)
        st.markdown(f"현재 DSR: {curr:.2f}% / 예상 DSR: {est:.2f}%")
        st.markdown(f"추천상품: {prod} / 한도: {lim:,}원 / {'가능' if ok else '불가'}")
        st.session_state.history.append({
            'type':'전세','time':datetime.now().strftime('%Y-%m-%d %H:%M'),
            'inputs':{'age':age,'income':income,'mp':mp,'je':je,'ho':ho,'rate':rate,'yrs':yrs},
            'result':{'current_dsr':curr,'estimated_dsr':est,'product':prod,'limit':lim,'approved':ok}
        })

elif page == "DSR 담보대출 계산기":
    st.title("🏦 DSR 담보대출 계산기 (스트레스 감면 포함)")
    annual_income = comma_number_input("연소득 (만원)", "dsr_income", "6000") * 10000
    region = st.selectbox("지역", list(LTV_MAP.keys()), key="dsr_region")
    first_home = st.checkbox("생애최초 주택 구입 여부", key="dsr_first")
    use_custom_ltv = st.checkbox("LTV 수동 입력", key="dsr_ltv")

    if use_custom_ltv:
        ltv_ratio = st.number_input("직접 LTV (%)", 0.0, 100.0, 70.0, 0.1, key="dsr_ltv_val") / 100
    elif first_home:
        ltv_ratio = 0.7
    else:
        ltv_ratio = LTV_MAP[region]

    price = comma_number_input("아파트 시세 (원)", "dsr_price", "500000000")
    st.markdown(f"▶ 시세: {price:,}원 | LTV: {ltv_ratio*100:.1f}%")

    st.subheader("기존 대출 내역")
    existing_loans = []
    cnt2 = st.number_input("기존 대출 건수", 0, 10, 0, key="dsr_cnt")
    for i in range(cnt2):
        amt2 = comma_number_input(f"대출 {i+1} 금액", f"dsr_amt{i}")
        yr2 = st.number_input(f"기간(년)", 1, 40, 10, key=f"dsr_yr{i}")
        rt2 = st.number_input(f"이율(%)", 0.0, 10.0, 4.0, key=f"dsr_rt{i}")
        existing_loans.append({"amount": amt2, "rate": rt2, "years": yr2, "repay_type": "만기일시"})

    st.subheader("신규 대출 조건")
    loan_type = st.selectbox("대출 유형", ["고정형","혼합형","변동형","주기형"], key="dsr_type")
    fixed_years = 0
    if loan_type == "혼합형":
        fixed_years = st.number_input("↳ 고정금리 적용 기간 (년)", 0, 100, 5, key="dsr_fix")
    total_years = st.number_input("↳ 총 대출 기간 (년)", 1, 100, 30, key="dsr_tot")

    cycle_level = None
    if loan_type == "주기형":
        cycle_mon = st.number_input("↳ 금리 리셋 주기 (개월)", 1, 120, 12, key="dsr_cycle")
        if cycle_mon >= 12:
            cycle_level = "1단계"
        elif cycle_mon >= 6:
            cycle_level = "2단계"
        else:
            cycle_level = "3단계"
        mult_prev = get_stress_multiplier(loan_type, fixed_years, total_years, cycle_level)
        st.info(f"▶ 주기형 {cycle_mon}개월 → {cycle_level}, 배율 {mult_prev:.1f}배")

    new_rate = st.number_input("신규 금리 (%)", 0.0, 10.0, 4.7, 0.01, key="dsr_newrate")
    new_amount = comma_number_input("신규 대출 금액 (원)", "dsr_newamt", "300000000")

    if st.button("계산하기", key="dsr_calc"):
        exist_mon2 = sum(
            calculate_monthly_payment(l["amount"], l["rate"], l["years"], l["repay_type"]) for l in existing_loans
        )
        dsr_lim = annual_income / 12 * DSR_RATIO
        avail = dsr_lim - exist_mon2

        mult2 = get_stress_multiplier(loan_type, fixed_years, total_years, cycle_level)
        stress_rate2 = new_rate * mult2
        discount2 = 1.5 if region in ["서울", "경기", "인천"] else 0.75
        adj_rate2 = stress_rate2 - discount2

        new_mon2 = calculate_monthly_payment(new_amount, adj_rate2, total_years, "만기일시")
        cap2 = min(price * ltv_ratio, 600_000_000 if first_home else price * ltv_ratio)

        st.write(f"기존 월 상환액: {exist_mon2:,.0f}원")
        st.write(f"DSR 한도: {dsr_lim:,.0f}원")
        st.write(f"여유 상환액: {avail:,.0f}원")
        st.write(f"스트레스 금리 (전): {stress_rate2:.2f}% → (감면 후) {adj_rate2:.2f}% (-{discount2:.2f}%p)")
        st.write(f"신규 월 상환액: {new_mon2:,.0f}원")
        st.write(f"LTV 한도: {ltv_ratio*100:.1f}% → {cap2:,.0f}원")

        if new_amount <= cap2 and new_mon2 <= avail:
            st.success("✅ 신규 대출 가능")
        else:
            st.error("❌ 신규 대출 불가")

elif page == "내 이력":
    st.title("⏳ 내 계산 이력")
    if st.session_state.history:
        for record in st.session_state.history:
            st.markdown(f"**[{record['time']}] {record['type']} 계산**")
            st.json(record)
    else:
        st.info("아직 계산 이력이 없습니다.")
   

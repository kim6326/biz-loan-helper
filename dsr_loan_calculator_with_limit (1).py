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
    ["DSR 담보대출 계산기", "전세대출 계산기"]
)

if page == "DSR 담보대출 계산기":
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
        existing_loans.append({"amount": amt2, "rate": rt2, "years": yr2, "repay_type": "원리금균등"})

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

        new_mon2 = calculate_monthly_payment(new_amount, adj_rate2, total_years, "원리금균등")
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

elif page == "전세대출 계산기":
    st.title("📊 전세대출 계산기")
    age = st.number_input("나이", 19, 60, 30)
    marital = st.radio("결혼 여부", ["미혼", "기혼"])
    income = comma_number_input("연소득 (만원)", "rent_inc", "6000") * 10000
    price = comma_number_input("시세 (원)", "rent_price", "500000000")
    deposit = comma_number_input("전세금 (원)", "rent_deposit", "400000000")
    hope = comma_number_input("희망 대출 (원)", "rent_hope", "200000000")
    agency = st.selectbox("보증기관", ["HUG", "SGI", "기타"])
    rate = st.number_input("이자율 (%)", 0.0, 10.0, 3.5)
    term = st.number_input("기간 (년)", 1, 5, 2)

    month_pay = calculate_monthly_payment(hope, rate, term, "원리금균등")
    burden = month_pay * 12 / income * 100
    limit = 200_000_000 if age < 34 or marital == "기혼" else 100_000_000
    is_youth = age <= 34 and income <= 70_000_000
    product = "청년 전세자금대출" if is_youth else "일반 전세자금대출"
    available = hope <= limit and burden <= 40

    st.write(f"💵 희망 월상환: {month_pay:,.0f}원")
    st.write(f"금융비용부담율: {burden:.2f}% (한도 40%)")
    st.write(f"추천상품: {product}")
    st.write(f"한도: {limit:,}원")

    if available:
        st.success("✅ 대출 가능")
    else:
        st.error("❌ 대출 불가")

    st.session_state.history.append({
        'type': '전세',
        'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'inputs': {
            'age': age,
            'marital': marital,
            'income': income,
            'price': price,
            'deposit': deposit,
            'hope': hope,
            'agency': agency,
            'rate': rate,
            'term': term
        },
        'results': {
            'product': product,
            'limit': limit,
            'burden': burden,
            'monthly_payment': month_pay,
            'available': available
        }
    })


    

import streamlit as st
import re
from datetime import datetime

st.set_page_config(
    page_title="대출 계산기 통합 앱",
    page_icon="🏦",
    layout="centered"
)

# LTV 및 DSR 비율 설정
LTV_MAP = {"서울": 0.7, "경기": 0.7, "인천": 0.7, "부산": 0.6, "기타": 0.6}
DSR_RATIO = 0.4

# 숫자 입력 및 콤마 출력 함수
def comma_number_input(label, key, value="0"):
    user_input = st.text_input(label, value=value, key=key)
    digits = re.sub(r'[^0-9]', '', user_input)
    formatted = f"{int(digits):,}" if digits else ""
    st.markdown(f"<div style='color:gray; font-size:0.9em;'>입력값: {formatted}</div>", unsafe_allow_html=True)
    return int(digits) if digits else 0

# 월 상환액 계산 함수
def calculate_monthly_payment(principal, rate, years, repay_type="원리금균등"):
    months = years * 12
    mr = rate / 100 / 12
    if repay_type == "원리금균등":
        if mr == 0:
            return principal / months
        return principal * mr * (1 + mr) ** months / ((1 + mr) ** months - 1)
    if repay_type == "원금균등":
        p = principal / months
        return p + principal * mr
    if repay_type == "만기일시":
        return principal * mr
    return 0

# 전세대출 상품 추천 함수
def recommend_product(age, married, income, market_price, jeonse_price, hope, org):
    max_limit = min(jeonse_price, market_price * 0.8)
    # 기관별 한도 설정
    if age <= 34 and income <= 70000000:
        limit = 200_000_000 if org == "HUG" else 100_000_000
        prod = "청년 전세자금대출"
    elif married and income <= 80000000:
        limit = 240_000_000
        prod = "신혼부부 전세자금대출"
    else:
        limit = 500_000_000
        prod = "일반 전세자금대출"
    # 실제 적용 한도
    applied_limit = min(max_limit, limit)
    approved = hope <= applied_limit
    return prod, applied_limit, approved

# 스트레스 배율 함수 (DSR 담보대출용)
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
        return {"1단계":1.4, "2단계":1.3, "3단계":1.2}[cycle_level]
    return 1.0

# 보증료율 설정 (전세대출 금융비용 부담 계산용)
FEE_RATES = {
    "HUG": {"loan": 0.0005, "deposit": 0.00128},
    "HF": {"loan": 0.0004, "deposit": 0.0},
    "SGI": {"loan": 0.00138, "deposit": 0.0}
}

# 세션 이력 초기화
if 'history' not in st.session_state:
    st.session_state.history = []

# 사이드바 메뉴
page = st.sidebar.selectbox(
    "계산기 선택",
    ["전세대출 계산기", "DSR 담보대출 계산기", "내 이력"]
)

if page == "전세대출 계산기":
    st.title("📊 전세대출 한도 계산기 with 비용부담율")
    age = st.number_input("나이", 19, 70, 32)
    married = st.radio("결혼 여부", ["미혼", "결혼"]) == "결혼"
    income_man = comma_number_input("연소득 (만원)", "inc", "6000")
    income = income_man * 10000
    mp = comma_number_input("시세 (원)", "mp", "500000000")
    je = comma_number_input("전세금 (원)", "je", "450000000")
    hope = comma_number_input("희망 대출 (원)", "hp", "300000000")
    org = st.selectbox("보증기관", ["HUG", "HF", "SGI"])
    rate = st.number_input("이자율 (%)", 0.0, 100.0, 3.5, 0.1)
    yrs = st.number_input("기간 (년)", 1, 30, 2)
    use_stress = st.checkbox("스트레스 금리 +0.6% 적용")
    eff_rate = rate + 0.6 if use_stress else rate

    st.markdown(f"💵 희망 월상환: {int(calculate_monthly_payment(hope, eff_rate, yrs, '만기일시')):,}원")

    st.subheader("기존 대출 내역")
    ex_loans = []
    cnt = st.number_input("기존 대출 건수", 0, 10, 0)
    for i in range(cnt):
        amt = comma_number_input(f"대출 {i+1} 금액", f"amt{i}")
        per = st.number_input(f"기간(년) {i+1}", 1, 40, 10, key=f"per{i}")
        rt = st.number_input(f"이율(%) {i+1}", 0.0, 100.0, 4.0, key=f"rt{i}")
        rp = st.selectbox(f"상환방식 {i+1}", ["원리금균등", "원금균등", "만기일시"], key=f"rp{i}")
        ex_loans.append({"amount": amt, "rate": rt, "years": per, "repay_type": rp})

    if st.button("계산"):
        prod, lim, base_ok = recommend_product(age, married, income, mp, je, hope, org)
        fr = FEE_RATES[org]
        annual_interest = hope * eff_rate / 100
        annual_fee = hope * fr['loan'] + je * fr['deposit']
        burden_pct = (annual_interest + annual_fee) / income * 100
        ok = base_ok and (burden_pct <= 40)

        # 결과 항상 출력 및 디버깅 정보
        st.markdown(f"추천상품: {prod}")
        st.markdown(f"한도: {int(lim):,}원")
        st.markdown(f"상환가능여부: {'✅ 가능' if ok else '❌ 불가'}")
        st.markdown(f"금융비용부담율: {burden_pct:.2f}% (한도 40%)")
        # 청년 분기 실패 시 일반 전세대출 한도 안내
        if prod == '청년 전세자금대출' and not base_ok:
            general_limit = int(min(je, mp * 0.8, 500_000_000))
            st.info(f"청년한도 초과 시 일반 전세대출 한도: {general_limit:,}원")
        # 디버깅용
        st.write(f"DEBUG → base_ok: {base_ok}, burden_check: {burden_pct <= 40}")

        st.session_state.history.append({
            'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'type': '전세',
            'result': {'limit': lim, 'approved': ok, 'burden_pct': burden_pct}
        })

elif page == "DSR 담보대출 계산기":
    st.title("🏦 DSR 담보대출 계산기")
        # 연소득 입력 (만원 단위)
    income_man = comma_number_input("연소득 (만원)", "di", "6000")
    income = income_man * 10000
    region = st.selectbox("지역", list(LTV_MAP.keys()))("지역", list(LTV_MAP.keys()))
    first_home = st.checkbox("생애최초 구매 여부")
    custom_ltv = st.checkbox("직접 LTV 입력")
    if custom_ltv:
        ltv = st.number_input("LTV (%)", 0.0, 100.0, 70.0, 0.1) / 100
    else:
        ltv = 0.7 if first_home else LTV_MAP[region]

    price = comma_number_input("시세 (원)", "dp", "500000000")
    st.markdown(f"▶ 시세: {price:,}원 | LTV: {ltv*100:.1f}%")

    st.subheader("기존 대출 내역")
    existing_loans = []
    cnt2 = st.number_input("기존 대출 건수", 0, 10, 0)
    for i in range(cnt2):
        amt2 = comma_number_input(f"대출 {i+1} 금액", f"da{i}")
        per2 = st.number_input(f"기간(년) {i+1}", 1, 40, 10, key=f"per2{i}")
        rt2 = st.number_input(f"이율(%) {i+1}", 0.0, 100.0, 4.0, key=f"rt2{i}")
        existing_loans.append({"amount": amt2, "rate": rt2, "years": per2, "repay_type": "만기일시"})

    st.subheader("신규 대출 조건")
    loan_type = st.selectbox("대출 유형", ["고정형", "혼합형", "변동형", "주기형"])
    fixed_years = 0
    if loan_type == "혼합형":
        fixed_years = st.number_input("↳ 고정금리 기간 (년)", 0, 100, 5)
    total_years = st.number_input("↳ 총 대출 기간 (년)", 1, 100, 30)

    cycle_level = None
    if loan_type == "주기형":
        cycle_mon = st.number_input("↳ 금리 리셋 주기 (개월)", 1, 120, 12)
        if cycle_mon >= 12:
            cycle_level = "1단계"
        elif cycle_mon >= 6:
            cycle_level = "2단계"
        else:
            cycle_level = "3단계"
        st.info(f"주기형: {cycle_mon}개월 → {cycle_level}")

    new_rate = st.number_input("신규 금리 (%)", 0.0, 100.0, 4.7, 0.1)
    new_amount = comma_number_input("신규 대출 금액 (원)", "na", "300000000")

    if st.button("계산2"):
        exist_monthly = sum(
            calculate_monthly_payment(l['amount'], l['rate'], l['years'], l['repay_type'])
            for l in existing_loans
        )
        dsr_limit = income / 12 * DSR_RATIO
        available = dsr_limit - exist_monthly

        mult = get_stress_multiplier(loan_type, fixed_years, total_years, cycle_level)
        stress_rate = new_rate * mult
        discount = 1.5 if region in ["서울", "경기", "인천"] else 0.75
        adjusted_rate = stress_rate - discount

        new_monthly = calculate_monthly_payment(new_amount, adjusted_rate, total_years, "만기일시")
        cap = min(price * ltv, 600_000_000 if first_home else price * ltv)

        st.write(f"기존 월 상환: {exist_monthly:,.0f}원")
        st.write(f"DSR 한도: {dsr_limit:,.0f}원")
        st.write(f"여유 상환: {available:,.0f}원")
        st.write(f"신규 월 상환: {new_monthly:,.0f}원")
        st.write(f"LTV 한도: {ltv*100:.1f}% → {cap:,.0f}원")

        if new_amount <= cap and new_monthly <= available:
            st.success("✅ 신규 대출 가능")
        else:
            st.error("❌ 신규 대출 불가")

else:
    st.title("⏳ 내 계산 이력")
    if st.session_state.history:
        for record in st.session_state.history:
            st.markdown(f"**[{record['time']}] {record['type']}**")
            st.json(record['result'])
    else:
        st.info("아직 계산 이력이 없습니다.")

  
       

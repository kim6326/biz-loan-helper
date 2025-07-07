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
    # 연소득 입력 (만원)
    income_man = comma_number_input("연소득 (만원)", "income_man", "6000")
    income = income_man * 10000
    # 아파트 시세 입력
    mp = comma_number_input("아파트 시세 (원)", "mp_input", "500000000")
    # 전세 보증금 입력
    je = comma_number_input("전세 보증금 (원)", "je_input", "450000000")
    # 희망 대출 금액 입력
    ho = comma_number_input("희망 대출 금액 (원)", "ho_input", "300000000")
    org = st.selectbox("보증기관", ["HUG", "HF", "SGI"])
    rate = st.number_input("이자율 (%)", 0.0, 10.0, 3.5, 0.1)
    yrs = st.number_input("기간 (년)", 1, 30, 2)("기간 (년)", 1, 30, 2)

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


# DSR 담보계산기 화면
elif page == "DSR 담보계산기":
    st.title("🏦 DSR 담보계산기 (스트레스 감면 포함)")

    # 소득 및 LTV 입력
    income2 = comma_number_input("연소득(원)", "inc2")
    region = st.selectbox("지역", list(LTV_MAP.keys()))
    fh = st.checkbox("생애최초")
    custom = st.checkbox("LTV 수동 입력")
    if custom:
        ltv = st.number_input("직접 LTV(%)", 0.0, 100.0, 70.0) / 100
    elif fh:
        ltv = 0.7
    else:
        ltv = LTV_MAP[region]

    # 시세 입력
    price = comma_number_input("시세(원)", "mp2")
    st.markdown(f"시세: {price:,}원 | LTV: {ltv*100:.1f}%")

    # 기존 담보 대출 내역
    existing_collateral_loans = []
    n2 = st.number_input("기존 담보 대출 건수", 0, 10, 0)
    for i in range(n2):
        a = comma_number_input(f"기존 대출 {i+1} 금액(원)", f"ca{i}")
        r = st.number_input(f"기존 대출 {i+1} 이율(%)", 0.0, 10.0, key=f"cr{i}")
        y = st.number_input(f"기존 대출 {i+1} 기간(년)", 1, 40, key=f"cy{i}")
        existing_collateral_loans.append({"amount": a, "rate": r, "years": y})

    # 신규 대출 조건
    lt = st.selectbox("상품 유형", ["고정형", "혼합형", "변동형", "주기형"])
    fy = 0
    if lt == "혼합형":
        fy = st.number_input("고정 금리 기간(년)", 0, 100, 5, key="fix2")
    ty = st.number_input("총 대출 기간(년)", 1, 100, 30, key="tot2")

    cl = None
    if lt == "주기형":
        cm = st.number_input("금리 리셋 주기(월)", 1, 120, 12, key="cm2")
        cl = "1단계" if cm >= 12 else "2단계" if cm >= 6 else "3단계"
        st.info(f"주기형 {cm}개월 → {cl}")

    nr = st.number_input("신규 이율(%)", 0.0, 10.0, 4.7, 0.01, key="nr2")
    na = comma_number_input("신규 담보 대출 금액(원)", "na2")
    use_stress2 = st.checkbox("📈 스트레스 금리 적용 (+0.6%)")
    er2 = nr + 0.6 if use_stress2 else nr
    st.markdown(f"고객 금리: {nr:.2f}%")
    if use_stress2:
        st.markdown(f"스트레스 금리: {er2:.2f}%")

    # 생활안정자금 추가
    want_life2 = st.checkbox("💼 생활안정자금 추가 신청")
    if want_life2:
        st.info("생활안정자금은 세입자 계좌로 입금되며 집주인 동의는 불필요합니다.")
        rl2 = st.selectbox("생활자금 지역", ["수도권", "지방"], key="rl2")
        mh2 = st.radio("주택 수", ["1주택", "다주택"], horizontal=True, key="mh2")
        if mh2 == "다주택":
            st.warning("다주택자는 신청 제한됩니다.")
        else:
            bl2 = 100000000 if rl2 == "수도권" else int(price * ltv)
            rem2 = max(0, bl2 - na)
            st.markdown(f"💡 생활안정자금 가능 한도: {rem2:,}원")
            ly2 = st.number_input("생활자금 기간(년)", 1, 10, 3, key="ly2")
            lrt2 = st.number_input("금리(%)", 0.0, 10.0, 4.13, key="lrt2")
            lam2 = st.number_input("신청 금액(원)", 0, rem2, 0, step=1000000, key="lam2")
            if lam2 > 0:
                lm2 = calculate_monthly_payment(lam2, ly2, lrt2)
                st.markdown(f"월 상환액: {int(lm2):,}원")

    # 계산 실행 및 결과
    if st.button("계산 담보"):        
        exist = sum(calculate_monthly_payment(loan['amount'], loan['years'], loan['rate']) for loan in existing_collateral_loans)
        dsr_limit = income2 / 12 * 0.4
        available = dsr_limit - exist
        new_payment = calculate_monthly_payment(na, ty, er2)
        cap = min(price * ltv, 600_000_000 if fh else int(price * ltv))

        st.write(f"기존 월 상환액: {exist:,.0f}원")
        st.write(f"DSR 한도(월): {dsr_limit:,.0f}원 | 여유 상환액: {available:,.0f}원")
        st.write(f"신규 월 상환액: {new_payment:,.0f}원")
        st.write(f"LTV 한도: {cap:,.0f}원")

        ok2 = na <= cap and new_payment <= available
        if ok2:
            st.success("✅ 신규 담보대출 가능")
        else:
            st.error("❌ 신규 담보대출 불가")

        # 최대 가능 담보대출
        mr = er2/100/12
        n = ty*12
        max_loan = (available*((1+mr)**n -1)/(mr*(1+mr)**n)) if mr>0 else available*n
        max_possible = int(min(max_loan, cap))
        st.markdown(f"🔁 최대 가능 담보대출금: **{max_possible:,}원**")

        # 이력 저장
        st.session_state.history.append({
            'type': '담보',
            'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'inputs': {'income': income2, 'region': region, 'ltv': ltv, 'price': price,
                       'new_amount': na, 'rate': nr, 'years': ty, 'stress': use_stress2},
            'result': {'available': available, 'new_payment': new_payment,
                       'limit': cap, 'approved': ok2, 'max_possible': max_possible}
        })

# 내 이력 페이지
else:
    st.title("⏳ 내 계산 이력")
    if st.session_state.history:
        for record in st.session_state.history:
            st.markdown(f"**[{record['time']}] {record['type']} 계산**")
            st.json(record)
    else:
        st.info("아직 계산 이력이 없습니다.")

 

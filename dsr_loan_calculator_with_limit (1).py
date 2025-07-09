import streamlit as st
import re
from datetime import datetime

st.set_page_config(
    page_title="대출 계산기 통합 앱",
    page_icon="\U0001f3e6",
    layout="centered"
)

LTV_MAP = {"서울": 0.7, "경기": 0.7, "인천": 0.7, "부산": 0.6, "기타": 0.6}
DSR_RATIO = 0.4

def comma_number_input(label, key, value="0"):
    user_input = st.text_input(label, value=value, key=key)
    digits = re.sub(r'[^0-9]', '', user_input)
    formatted = f"{int(digits):,}" if digits else ""
    st.markdown(f"<div style='color:gray; font-size:0.9em;'>입력값: {formatted}</div>", unsafe_allow_html=True)
    return int(digits) if digits else 0

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

if 'history' not in st.session_state:
    st.session_state.history = []

page = st.sidebar.selectbox("계산기 선택", ["DSR 담보대출 계산기", "전세대출 계산기", "내 계산 이력"])

if page == "DSR 담보대출 계산기":
    st.title("\U0001f3e6 DSR 담보대출 계산기 (스트레스 감면 포함)")
    annual_income = comma_number_input("연소득 (만원)", "inc", "6000") * 10000
    region = st.selectbox("지역", list(LTV_MAP.keys()))
    first_home = st.checkbox("생애최초 구매 여부")
    custom_ltv = st.checkbox("LTV 수동 입력")
    ltv_ratio = st.number_input("LTV (%)", 0.0, 100.0, 70.0, 0.1) / 100 if custom_ltv else (0.7 if first_home else LTV_MAP[region])
    price = comma_number_input("시세 (원)", "pp", "500000000")
    st.markdown(f"▶ 시세: {price:,}원 | LTV: {ltv_ratio*100:.1f}%")

    st.subheader("기존 대출 내역")
    existing_loans = []
    cnt = st.number_input("기존 대출 건수", 0, 10, 0)
    apply_stress_to_existing = st.checkbox("기존 대출에도 스트레스 금리 적용")
    for i in range(cnt):
        amt = comma_number_input(f"대출 {i+1} 금액", f"amt{i}")
        yr = st.number_input(f"기간(년) {i+1}", 1, 40, 10, key=f"yr{i}")
        rt = st.number_input(f"이율(%) {i+1}", 0.0, 10.0, 4.0, key=f"rt{i}")
        repay = st.selectbox(f"상환방식 {i+1}", ["원리금균등", "원금균등", "만기일시"], key=f"rep{i}")
        stress_rt = rt * 1.6 - (1.5 if region in ["서울", "경기", "인천"] else 0.75) if apply_stress_to_existing else rt
        existing_loans.append({'amount': amt, 'rate': stress_rt, 'years': yr, 'repay_type': repay})

    # === 여기서 청년/신혼 체크박스 추가 ===
    is_young = st.checkbox("청년 전세 대상자 여부 (만 34세 이하)")
    is_newlywed = st.checkbox("신혼부부 특례 적용")
    # === 여기까지 ===

    loan_type = st.selectbox("대출 유형", ["고정형", "혼합형", "변동형", "주기형"])
    fixed_years = st.number_input("고정금리 기간(년)", 0, 30, 5) if loan_type == "혼합형" else 0
    total_years = st.number_input("총 대출 기간(년)", 1, 40, 30)
    cycle_level = None
    if loan_type == "주기형":
        cm = st.number_input("금리 리셋 주기(개월)", 1, 120, 12)
        cycle_level = "1단계" if cm >= 12 else ("2단계" if cm >= 6 else "3단계")
        st.info(f"주기형 {cm}개월 → {cycle_level}")

    new_rate = st.number_input("신규 금리(%)", 0.0, 10.0, 4.7)
    new_amt = comma_number_input("신규 대출 금액(원)", "na", "300000000")

    if st.button("계산하기"):
        dsr_ratio = 0.4
        if is_young:
            dsr_ratio = 1.0  # 청년은 사실상 DSR 미적용 효과
        elif is_newlywed:
            dsr_ratio = 0.6  # 신혼부부는 DSR 완화

        calc_time = datetime.now().strftime('%Y-%m-%d %H:%M')
        exist_mon = sum(calculate_monthly_payment(l['amount'], l['rate'], l['years'], l['repay_type']) for l in existing_loans)
        dsr_limit = annual_income * dsr_ratio / 12
        avail = dsr_limit - exist_mon
        mult = get_stress_multiplier(loan_type, fixed_years, total_years, cycle_level)
        stress = new_rate * mult
        disc = 1.5 if region in ["서울", "경기", "인천"] else 0.75
        adj = max(stress - disc, new_rate)
        repay_type = "원리금균등" if loan_type == "고정형" else "만기일시"
        new_mon = calculate_monthly_payment(new_amt, adj, total_years, repay_type)
        cap = min(price * ltv_ratio, 600_000_000 if first_home else price * ltv_ratio)
        st.write(f"기존 월 상환: {exist_mon:,.0f}원")
        st.write(f"DSR 한도: {dsr_limit:,.0f}원")
        st.write(f"여유 상환: {avail:,.0f}원")
        st.write(f"신규 월 상환: {new_mon:,.0f}원")
        st.write(f"LTV 한도: {cap:,.0f}원")
        months = total_years * 12
        mr = adj / 100 / 12
        max_dsr = (avail * ((1+mr)**months - 1) / (mr * (1+mr)**months)) if repay_type == "원리금균등" and mr > 0 else (avail / mr if mr > 0 else cap)
        max_loan = min(max_dsr, cap)
        st.info(f"✨ 최대 대출 가능금액(DSR/LTV 기준): {int(max_loan):,}원")
        approved = new_amt <= max_loan
        st.success("✅ 신규 대출 가능") if approved else st.error("❌ 신규 대출 불가능")
        st.session_state.history.append({
            'type': '담보', 'time': calc_time,
            'inputs': {'income': annual_income,'region': region,'price': price,'ltv_ratio': ltv_ratio,'new_amt': new_amt,'new_rate': new_rate,'years': total_years},
            'result': {'existing_payment': exist_mon,'new_payment': new_mon,'limit': dsr_limit,'max_loan': max_loan,'approved': approved}
        })

elif page == "전세대출 계산기":
    st.title("\U0001f4ca 전세대출 한도 계산기 with DSR")
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
        st.markdown(f"\U0001f4b5 희망 대출 월 상환액: {int(ho_mon):,}원")

    sample_amt = comma_number_input("예시 대출금액 (원)", "sample_amt", "500000000")
    example_mon = calculate_monthly_payment(sample_amt, effective_rate, yrs, repay_type)
    st.markdown(f"\U0001f4cc 예시 {sample_amt:,}원 월 상환액: {int(example_mon):,}원")

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
        estimated_rate = st.number_input("추정금리 (%)", 0.0, 10.0, 5.0, 0.1)
        total_existing_amount = sum(l["amount"] for l in existing_loans)
        financial_burden = ((total_existing_amount * (estimated_rate / 100)) + (ho * (rate / 100))) / income * 100
        st.markdown(f"📊 금융비용부담비율: **{financial_burden:.2f}%** {'✅ 통과' if financial_burden <= 40 else '❌ 초과'}")
        max_monthly = income / 12 * DSR_RATIO - sum(calculate_monthly_payment(l["amount"], l["rate"], l["years"], l["repay_type"]) for l in existing_loans)
        if effective_rate > 0 and yrs > 0:
            realistic_limit = min(
                max_monthly / (effective_rate / 100 / 12),
                je * 0.8,
                500_000_000
            )
            st.markdown(f"📈 역산 최대 대출 가능 금액(현실 적용 기준): **{int(realistic_limit):,}원**")
            st.caption("※ 보증금 80% 한도 및 보증기관 최대 5억원 기준 제한 적용")
        curr = sum(calculate_monthly_payment(l["amount"], l["rate"], l["years"], l["repay_type"]) for l in existing_loans)
        est = curr + calculate_monthly_payment(ho, effective_rate, yrs, repay_type)
        limit = income / 12 * DSR_RATIO
        approved = est <= limit
        st.markdown(f"현재 월 상환액: {curr:,.0f}원 / 예상 총 상환액: {est:,.0f}원")
        st.markdown(f"DSR 기준 한도: {limit:,.0f}원 / {'가능' if approved else '불가'}")
        st.session_state.history.append({
            'type':'전세','time':datetime.now().strftime('%Y-%m-%d %H:%M'),
            'inputs':{'age':age,'income':income,'mp':mp,'je':je,'ho':ho,'rate':rate,'yrs':yrs},
            'result':{'current_dsr':curr,'estimated_dsr':est,'limit':limit,'approved':approved}
        })

elif page == "내 계산 이력":
    st.title("\U0001f552 내 계산 이력")
    if st.session_state.history:
        for h in st.session_state.history[::-1]:
            st.markdown(f"**[{h['time']}] {h['type']} 계산**")
            st.json(h)
    else:
        st.info("아직 계산 이력이 없습니다.")

import streamlit as st
import re
from datetime import datetime

st.set_page_config(
    page_title="DSR 담보계산기",
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
        st.caption(f"시세: {mp:,}원")
    except:
        mp = 0
        st.error("숫자만 입력하세요.")

    raw_je = st.text_input("전세 보증금 (원)", "450000000")
    try:
        je = int(raw_je.replace(',', ''))
        st.caption(f"전세금: {je:,}원")
    except:
        je = 0
        st.error("숫자만 입력하세요.")

    raw_ho = st.text_input("희망 대출 금액 (원)", "300000000")
    try:
        ho = int(raw_ho.replace(',', ''))
        st.caption(f"희망대출: {ho:,}원")
    except:
        ho = 0
        st.error("숫자만 입력하세요.")

    org = st.selectbox("보증기관", ["HUG", "HF", "SGI"])
    rate = st.number_input("이자율 (%)", 0.0, 10.0, 3.5, 0.1)
    yrs = st.number_input("기간 (년)", 1, 30, 2)

    num = st.number_input("기존 대출 건수", 0, 10, 0)
    el = []
    for i in range(num):
        amt = comma_number_input(f"{i+1}대출금액", f"a{i}")
        pr = st.number_input(f"{i+1}대출기간(년)", 1, 40, 10, key=f"p{i}")
        rt = st.number_input(f"{i+1}이자율(%)", 0.0, 10.0, 4.0, key=f"r{i}")
        rp = st.selectbox(f"{i+1}상환방식", ["원리금균등", "원금균등", "만기일시"], key=f"rp{i}")
        el.append({"amount":amt, "period":pr, "rate":rt, "repay_type":rp})

    if st.button("계산"):        
        curr = calculate_dsr(el, income)
        est = calculate_dsr(el + [{"amount":ho, "period":yrs, "rate":rate, "repay_type":"원리금균등"}], income)
        prod, lim, ok = recommend_product(age, married, income, mp, ho, org)
        st.markdown(f"현재 DSR: {curr:.2f}% / 예상 DSR: {est:.2f}%")
        st.markdown(f"추천상품: {prod} / 한도: {lim:,}원 / 가능여부: {'가능' if ok else '불가'}")

else:
    st.title("🏦 DSR 담보계산기 (스트레스 감면 포함)")
    income = comma_number_input("연소득(원)", "inc2")
    region = st.selectbox("지역", list(LTV_MAP.keys()))
    fh = st.checkbox("생애최초")
    custom = st.checkbox("LTV수동")
    if custom:
        ltv = st.number_input("LTV(%)", 0.0, 100.0, 70.0) / 100
    elif fh:
        ltv = 0.7
    else:
        ltv = LTV_MAP[region]

    price = comma_number_input("시세(원)", "mp2")
    st.markdown(f"시세: {price:,}원 | LTV: {ltv*100:.1f}%")

    el2 = []
    n2 = st.number_input("기존건수", 0, 10, 0)
    for i in range(n2):
        a = comma_number_input(f"기존{i+1}금액", f"ba{i}")
        r = st.number_input(f"기존{i+1}이율(%)", key=f"br{i}")
        y = st.number_input(f"기존{i+1}기간", 1, 40, key=f"by{i}")
        el2.append({"amount":a, "rate":r, "years":y})

    lt = st.selectbox("유형", ["고정형", "혼합형", "변동형", "주기형"])
    fy = 0
    if lt == "혼합형":
        fy = st.number_input("고정년수", 0, 100, 5, key="fix2")
    ty = st.number_input("총년수", 1, 100, 30, key="tot2")

    cl = None
    if lt == "주기형":
        cm = st.number_input("주기(월)", 1, 120, 12, key="cm2")
        cl = "1단계" if cm >= 12 else "2단계" if cm >= 6 else "3단계"
        st.info(f"주기형 {cm}개월 → {cl}")

    nr = st.number_input("신규이율(%)", 0.0, 10.0, 4.7, 0.01, key="nr2")
    na = comma_number_input("신규금액", "na2")
    use_stress = st.checkbox("스트레스 적용")
    er = nr + 0.6 if use_stress else nr
    st.markdown(f"고객금리: {nr:.2f}%")
    if use_stress:
        st.markdown(f"스트레스금리: {er:.2f}%")

    want = st.checkbox("생활자금 신청")
    if want:
        st.info("ℹ️ 생활안정자금은 세입자 본인 명의로 실행되며, 집주인 동의는 불필요합니다. 전세자금대출과 달리 임대차와 무관한 생활비 용도 대출이기 때문입니다.")
        rl = st.selectbox("지역", ["수도권", "지방"], key="rl2")
        mh = st.radio("주택수", ["1주택", "다주택"], horizontal=True)
        if mh == "다주택":
            st.warning("불가")
        else:
            bl = 100000000 if rl == "수도권" else int(price * ltv)
            rem = max(0, bl - na)
            if rem > 0:
                st.markdown(f"잔여: {rem:,}원")
                ly = st.number_input("년수", 1, 10, 3, key="ly2")
                lr = st.number_input("이율(%)", 0.0, 10.0, 4.13, key="lr2")
                la = st.number_input("신청금액", 0, rem, 0, 1000000, key="la2")
                if la > 0:
                    m = calculate_monthly_payment(la, ly, lr)
                    st.markdown(f"월상환: {int(m):,}원")
            else:
                st.warning("잔여없음")

    if st.button("계산"):
        exist = sum(calculate_monthly_payment(l["amount"], l["rate"], l["years"]) for l in el2)
        dsr = income / 12 * 0.4 - exist
        nm = calculate_monthly_payment(na, ty, er)
        cap = min(price * ltv, 600000000 if fh else int(price * ltv))
        st.write(f"기존: {exist:,.0f}원 | 여유: {dsr:,.0f}원 | 신규: {nm:,.0f}원 | 한도: {cap:,.0f}원")
        if na <= cap and nm <= dsr:
            st.success("가능")
        else:
            st.error("불가")
    st.subheader("최대 계산")
    cr = st.number_input("계산이율", 0.0, 10.0, 4.7, 0.01, key="cr2")
    cy = st.number_input("계산년수", 1, 100, 30, key="cy2")
    if st.button("최대계산"):
        e = sum(calculate_monthly_payment(l["amount"], l["rate"], l["years"]) for l in el2)
        av = income / 12 * 0.4 - e
        mm = get_stress_multiplier(lt, fy, ty, cl)
        mr = (cr * mm) / 100 / 12
        nn = cy * 12
        ml = (av * ((1 + mr)**nn - 1) / (mr * (1 + mr)**nn)) if mr > 0 else av * nn
        cp = min(price * ltv, 600000000 if fh else int(price * ltv))
        if ml > 0:
            st.success(f"최대: {min(ml, cp):,.0f}원")
        else:
            st.error("불가")


 

import streamlit as st
import re
from datetime import datetime

st.set_page_config(
    page_title="대출 계산기 통합 앱",
    page_icon="🏦",
    layout="centered"
)

# ─── LTV 및 DSR 비율 설정 ──────────────────────────────────
LTV_MAP = {"서울": 0.7, "경기": 0.7, "인천": 0.7, "부산": 0.6, "기타": 0.6}
DSR_RATIO = 0.4
# ────────────────────────────────────────────────────────

# 숫자 입력 및 콤마 출력
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
        if mr == 0: return principal / months
        return principal * mr * (1 + mr) ** months / ((1 + mr) ** months - 1)
    if repay_type == "원금균등":
        p = principal / months
        return p + principal * mr
    if repay_type == "만기일시":
        return principal * mr
    return 0

# DSR 계산 함수
def calculate_dsr(loans, annual_income):
    total = sum(calculate_monthly_payment(l['amount'], l['rate'], l['years'], l['repay_type']) * 12 for l in loans)
    return (total / annual_income * 100) if annual_income > 0 else 0

# 전세대출 상품 추천 함수
def recommend_product(age, married, income, market_price, jeonse_price, hope, org):
    max_limit = min(jeonse_price, market_price * 0.8)
    if age <= 34 and income <= 70000000:
        lim = 200_000_000 if org == "HUG" else 100_000_000
        prod = "청년 전세자금대출"
    elif married and income <= 80000000:
        lim = 240_000_000
        prod = "신혼부부 전세자금대출"
    else:
        lim = 500_000_000
        prod = "일반 전세자금대출"
    return prod, min(max_limit, lim), (hope <= min(max_limit, lim))

# 스트레스 배율 함수 (담보대출용)
def get_stress_multiplier(loan_type, fix_years, tot_years, cycle=None):
    if loan_type == "고정형": return 1.0
    if loan_type == "변동형": return 2.0
    if loan_type == "혼합형":
        r = fix_years / tot_years if tot_years else 0
        if r >= 0.8: return 1.0
        if r >= 0.6: return 1.4
        if r >= 0.4: return 1.8
        return 2.0
    if loan_type == "주기형" and cycle:
        return {"1단계":1.4, "2단계":1.3, "3단계":1.2}.get(cycle, 1.0)
    return 1.0

# 세션 이력 초기화
if 'history' not in st.session_state:
    st.session_state.history = []

# 사이드바
page = st.sidebar.selectbox("계산기 선택", ["전세대출 계산기", "DSR 담보대출 계산기", "내 이력"])

# 보증료율 (전세)
FEE_RATES = {"HUG":{'loan':0.0005,'deposit':0.00128},"HF":{'loan':0.0004,'deposit':0},"SGI":{'loan':0.00138,'deposit':0}}

if page == "전세대출 계산기":
    st.title("📊 전세대출 한도 계산기")
    age = st.number_input("나이",19,70,32)
    married = st.radio("결혼 여부",["미혼","결혼"])=="결혼"
    income = comma_number_input("연소득 (만원)","inc","6000")*10000
    mp = comma_number_input("시세 (원)","mp","500000000")
    je = comma_number_input("전세금 (원)","je","450000000")
    hope = comma_number_input("희망 대출 (원)","hp","300000000")
    org = st.selectbox("보증기관",["HUG","HF","SGI"])
    rate = st.number_input("이자율 (%)",0.0,100.0,3.5,0.1)
    yrs = st.number_input("기간 (년)",1,30,2)
    use_stress = st.checkbox("스트레스 금리 +0.6% 적용")
    eff_rate = rate+0.6 if use_stress else rate

    st.markdown(f"💵 희망 월상환: {int(calculate_monthly_payment(hope,eff_rate,yrs,'만기일시')):,}원")

    st.subheader("기존 대출")
    ex_loans = []
    cnt = st.number_input("기존 대출 건수", 0, 10, 0, key='cnt')
    for i in range(cnt):
        a = comma_number_input(f"대출 {i+1} 금액", f"a{i}")
        y = st.number_input(f"기간(년) {i+1}", 1, 40, 10, key=f"y{i}")
        r = st.number_input(f"이율(%) {i+1}", 0.0, 100.0, 4.0, key=f"r{i}")
        rp = st.selectbox(f"상환방식 {i+1}", ["원리금균등", "원금균등", "만기일시"], key=f"rp{i}")
        ex_loans.append({'amount': a, 'rate': r, 'years': y, 'repay_type': rp})

    if st.button("계산"): ("계산"): 
        prod,lim,ok= recommend_product(age,married,income,mp,je,hope,org)
        fr=FEE_RATES[org]
        ai=hope*eff_rate/100
        af=hope*fr['loan']+je*fr['deposit']
        burden= (ai+af)/income*100
        ok= ok and burden<=40
        st.markdown(f"한도: {int(lim):,}원 / {'가능' if ok else '불가'}")
        st.markdown(f"비용부담율: {burden:.2f}%")
        st.markdown(f"추천상품: {prod}")
        st.session_state.history.append({'time':datetime.now().strftime('%Y-%m-%d %H:%M'),'type':'전세','result':{'limit':lim,'approved':ok,'burden':burden}})

elif page=="DSR 담보대출 계산기":
    st.title("🏦 DSR 담보대출 계산기")
    income=comma_number_input("연소득 (만원)","di","6000")*10000
    reg=st.selectbox("지역",list(LTV_MAP.keys()))
    first=st.checkbox("생애최초")
    ltv=st.number_input("LTV (%)",0.0,100.0,70.0)/100 if st.checkbox("직접 입력") else (0.7 if first else LTV_MAP[reg])
    price=comma_number_input("시세 (원)","dp","500000000")
    ex=[]
    for i in range(st.number_input("기존건수",0,10,0,key='dc')):
        a=comma_number_input(f"금액{i}",f"da{i}")
        y=st.number_input(f"기간{i}",1,40,10,key=f"dy{i}")
        r=st.number_input(f"이율{i}",0.0,100.0,4.0,key=f"dr{i}")
        ex.append({'amount':a,'rate':r,'years':y,'repay_type':'만기일시'})
    st.subheader("신규 대출")
    lt=st.selectbox("유형",["고정형","혼합형","변동형","주기형"])
    fy=st.number_input("고정년",0,100,5) if lt=="혼합형" else 0
    ty=st.number_input("총년",1,100,30)
    cycle=None
    if lt=="주기형":
        cm=st.number_input("주기(개월)",1,120,12)
        cycle="1단계" if cm>=12 else ("2단계" if cm>=6 else "3단계")
        st.info(f"주기형 {cm}개월 → {cycle}")
    nr=st.number_input("금리 (%)",0.0,100.0,4.7)
    na=comma_number_input("금액 (원)","na","300000000")
    if st.button("계산2"):  
        exist=sum(calculate_monthly_payment(l['amount'],l['rate'],l['years'],l['repay_type']) for l in ex)
        dsr_lim=income/12*DSR_RATIO
        avail=dsr_lim-exist
        mult=get_stress_multiplier(lt,fy,ty,cycle)
        sr=nr*mult
        disc=1.5 if reg in ["서울","경기","인천"] else 0.75
        adj=sr-disc
        newm=calculate_monthly_payment(na,adj,ty,'만기일시')
        cap=min(price*ltv,600_000_000 if first else price*ltv)
        st.write(f"기존 월: {exist:,.0f}원")
        st.write(f"DSR한도: {dsr_lim:,.0f}원")
        st.write(f"여유: {avail:,.0f}원")
        st.write(f"신규월: {newm:,.0f}원")
        st.write(f"LTV한도: {ltv*100:.1f}% → {cap:,.0f}원")          
        if na<=cap and newm<=avail:
            st.success("가능")
        else:
            st.error("불가")

else:
    st.title("⏳ 내 이력")
    if st.session_state.history:
        for r in st.session_state.history:
            st.markdown(f"**[{r['time']}] {r['type']}**")
            st.json(r.get('result', {}))
    else:
        st.info("이력 없음.")

 

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# ----------------------------------------------------------------
# 0. 페이지 설정 및 데이터 로드
# ----------------------------------------------------------------
st.set_page_config(page_title="통합 주문 데이터 분석 대시보드", layout="wide")

@st.cache_data
def load_and_process_data():
    # 깃허브 배포 및 로컬 환경 모두 지원하도록 스크립트 위치 기준 경로 사용
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_name = "project1-preprocessed_data.csv"
    file_path = os.path.join(base_dir, file_name)
    
    # 만약 파일이 없으면 기존에 사용하던 다른 이름이나 경로도 확인 (백업 로직)
    if not os.path.exists(file_path):
        alt_name = "project1 - preprocessed_data.csv"
        alt_path = os.path.join(base_dir, alt_name)
        if os.path.exists(alt_path):
            file_path = alt_path
        elif os.path.exists(r"D:\fcicb6\project1 - preprocessed_data.csv"):
            file_path = r"D:\fcicb6\project1 - preprocessed_data.csv"
        else:
            return None
    
    df = pd.read_csv(file_path)
    
    # 금액 데이터 숫자형 변환
    price_cols = ['실결제 금액', '결제금액', '판매단가', '공급단가']
    for col in price_cols:
        if col in df.columns and df[col].dtype == 'object':
            df[col] = df[col].str.replace(',', '').astype(float)
    
    # 날짜 처리
    df['주문일'] = pd.to_datetime(df['주문일'])
    df['주문날짜'] = df['주문일'].dt.date
    
    # 인플루언서 그룹핑
    df['그룹'] = df['셀러명'].apply(lambda x: '킹댕즈' if x == '킹댕즈' else '일반 셀러')
    
    # 4. 재구매 정의 수정 (사용자 요청: 주문일이 다른 날짜인 경우만 재구매로 인정)
    # 고객 식별은 '주문자연락처'를 기준으로 합니다.
    df = df.sort_values(by=['주문자연락처', '주문일'])
    
    # 각 고객별로 주문날짜의 순서를 매깁니다 (첫 방문일=0, 이후 방문날짜마다 +1)
    df['재구매_날짜순서'] = df.groupby('주문자연락처')['주문날짜'].transform(lambda x: x.map({d: i for i, d in enumerate(sorted(x.unique()))}))
    df['재구매여부'] = df['재구매_날짜순서'] > 0
    df['최초주문일'] = df.groupby('주문자연락처')['주문날짜'].transform('min')
    
    # 5. 구매 목적 분류 (Heuristic: 과수 크기와 가격대를 조합하여 추정)
    def classify_purpose(row):
        size = str(row['과수 크기'])
        price = row['실결제 금액']
        # 선물용 키워드가 있거나, 로얄과이면서 고단가인 경우
        if any(keyword in size for keyword in ['선물', '명품', '로얄', '특']) or (price >= 35000):
            return '선물용'
        else:
            return '개인소비용'
    
    df['구매목적'] = df.apply(classify_purpose, axis=1)
    
    # 6. 구매 시점 클러스터링 (요일 x 시간 패턴)
    def classify_time_cluster(row):
        hr = row['주문일'].hour
        dy = row['주문일'].dayofweek # 0:월, 5:토, 6:일
        
        if dy >= 5: # 주말
            if 0 <= hr < 7: return 0 # 주말 새벽
            else: return 2 # 주말 피크
        else: # 평일
            if 0 <= hr < 7: return 3 # 평일 새벽
            else: return 1 # 평일 피크
            
    df['time_cluster'] = df.apply(classify_time_cluster, axis=1)
    
    return df

df = load_and_process_data()

if df is None:
    st.error("데이터 파일을 찾을 수 없습니다. 경로를 확인해주세요.")
    st.stop()

# ----------------------------------------------------------------
# 1. 사이드바 필터
# ----------------------------------------------------------------
st.sidebar.title("🔍 분석 필터")
selected_groups = st.sidebar.multiselect(
    "분석할 셀러 그룹",
    options=['킹댕즈', '일반 셀러'],
    default=['킹댕즈', '일반 셀러']
)

if not selected_groups:
    st.warning("분석할 그룹을 선택해주세요.")
    st.stop()

f_df = df[df['그룹'].isin(selected_groups)]

# ----------------------------------------------------------------
# 2. 메인 화면 및 핵심 지표
# ----------------------------------------------------------------
st.title("🍊 통합 과일 주문 데이터 분석 대시보드")
st.markdown("---")

col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1:
    st.metric("총 매출액", f"₩{f_df['실결제 금액'].sum():,.0f}")
with col_m2:
    st.metric("총 주문건수", f"{len(f_df):,}건")
with col_m3:
    st.metric("평균 객단가", f"₩{f_df['실결제 금액'].mean():,.0f}")
with col_m4:
    repeat_rate = f_df['재구매여부'].mean() * 100
    st.metric("재구매 비중 (날짜기준)", f"{repeat_rate:.1f}%")

# ----------------------------------------------------------------
# 3. 탭 구성 (EDA 및 상세 분석)
# ----------------------------------------------------------------
tab_dash, tab1, tab2, tab_prod, tab_funnel, tab_time, tab_grade, tab3, tab4, tab_growth, tab5, tab6 = st.tabs([
    "🚀 Dashboard", "📈 매출 & 채널", "📊 셀러 & 로열티", "📦 상품 페이지 분석", "🔁 재구매 퍼널", "⏰ 구매 시점 분석", "💎 등급별 분석", "🗺️ 지역별 분석", "🔍 경로 상세분석", "🎯 셀러 성장 전략", "🚀 마케팅 전략", "📋 전체데이터"
])

# --- 탭 0: Dashboard (신규 메인) ---
with tab_dash:
    st.title("Dashboard")
    st.markdown("<p style='color: #666; font-size: 1.1rem; margin-top: -15px;'>비즈니스 성과를 한눈에 파악하세요</p>", unsafe_allow_html=True)
    
    # 데이터 준비: 주차별/일별 실적
    f_df['주차'] = pd.to_datetime(f_df['주문날짜']).dt.isocalendar().week
    f_df['주문일_DT'] = pd.to_datetime(f_df['주문일'])
    
    # WoW 계산용
    weekly_stats = f_df.groupby('주차').agg({
        '실결제 금액': 'sum',
        '주문자연락처': 'nunique'
    }).reset_index()
    
    if len(weekly_stats) >= 2:
        curr_w = weekly_stats.iloc[-1]
        prev_w = weekly_stats.iloc[-2]
        
        rev_wow = ((curr_w['실결제 금액'] - prev_w['실결제 금액']) / prev_w['실결제 금액'] * 100)
        cust_wow = ((curr_w['주문자연락처'] - prev_w['주문자연락처']) / prev_w['주문자연락처'] * 100)
    else:
        rev_wow, cust_wow = 0, 0

    # 상단 KPI 카드 (Premium Style)
    st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 2.2rem !important; font-weight: 700 !important; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #f0f2f6; box-shadow: 0 4px 6px rgba(0,0,0,0.02); }
    </style>
    """, unsafe_allow_html=True)

    c_kpi1, c_kpi2, c_kpi3, c_kpi4 = st.columns(4)
    with c_kpi1:
        st.metric("TOTAL REVENUE", f"₩{f_df['실결제 금액'].sum():,.0f}", f"{rev_wow:+.1f}% vs last week")
    with c_kpi2:
        st.metric("ACTIVE CUSTOMERS", f"{f_df['주문자연락처'].nunique():,}명", f"{cust_wow:+.1f}% vs last week")
    with c_kpi3:
        # 평균 결제액
        avg_rev = f_df['실결제 금액'].mean()
        st.metric("AVG TRANSACTION", f"₩{avg_rev:,.0f}")
    with c_kpi4:
        # 총 주문건수
        st.metric("TOTAL ORDERS", f"{len(f_df):,}건")

    st.markdown("<br>", unsafe_allow_html=True)

    # 메인 차트 영역
    c_chart1, c_chart2 = st.columns(2)
    
    with c_chart1:
        st.write("**Revenue vs Date**")
        daily_rev = f_df.groupby('주문날짜')['실결제 금액'].sum().reset_index()
        fig_rev_line = px.area(daily_rev, x='주문날짜', y='실결제 금액',
                               color_discrete_sequence=['#00C897'])
        fig_rev_line.update_traces(line_shape='spline', line=dict(width=4))
        fig_rev_line.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='#f0f2f6'),
            margin=dict(l=0, r=0, t=20, b=0),
            height=350
        )
        st.plotly_chart(fig_rev_line, use_container_width=True)

    with c_chart2:
        st.write("**Customer Growth**")
        # 누적 고객 수 계산
        first_orders = f_df.sort_values('주문일').drop_duplicates('주문자연락처')
        daily_new_cust = first_orders.groupby('주문날짜').size().reset_index(name='신규고객')
        daily_new_cust['누적고객'] = daily_new_cust['신규고객'].cumsum()
        
        fig_cust_line = px.line(daily_new_cust, x='주문날짜', y='누적고객',
                                color_discrete_sequence=['#636EFA'], markers=True)
        fig_cust_line.update_traces(line_shape='spline', line=dict(width=4))
        fig_cust_line.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='#f0f2f6'),
            margin=dict(l=0, r=0, t=20, b=0),
            height=350
        )
        st.plotly_chart(fig_cust_line, use_container_width=True)

    st.markdown("---")

    # ⚠️ 취소 리스크 분석 (상시 노출)
    st.write("#### ⚠️ 최근 상품 옵션별 취소 현황 분석")
    cancel_df = f_df[f_df['취소여부'] == 'Y']
    if not cancel_df.empty:
        option_cancel = cancel_df.groupby(['상품명', '과수 크기']).size().reset_index(name='취소건수')
        option_cancel = option_cancel.sort_values('취소건수', ascending=False).head(10)
        st.dataframe(option_cancel.style.background_gradient(subset=['취소건수'], cmap='Reds'),
                     use_container_width=True, hide_index=True)
    else:
        st.success("최근 취소 발생 건이 없습니다. 모든 운영이 원활합니다.")


# --- 탭 1: 매출 & 채널 ---
with tab1:
    st.subheader("🎯 마케팅 운영 효율 상세 분석")
    st.markdown("""
    일별 매출과 셀러 활동성을 교차 분석하여 **운영 효율성**을 진단합니다. 
    셀러가 특정 요일에 몰린다면 해당 시점의 **경쟁 밀도**를 파악하고 광고 집행 시점을 조절해야 합니다.
    """)

    # 1. 요일별 매출 및 셀러 활동성 (마케팅 타이밍 결정)
    st.write("#### 1️⃣ 요일별 마케팅 효율 (어느 요일에 예산을 쓸 것인가?)")
    f_df['요일'] = f_df['주문일'].dt.day_name()
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    weekday_stats = f_df.groupby(['요일', '그룹']).agg({
        '실결제 금액': 'sum',
        '셀러명': 'nunique'
    }).reindex(day_order, level=0).reset_index()
    
    c1, c2 = st.columns(2)
    with c1:
        fig_day_rev = px.bar(weekday_stats, x='요일', y='실결제 금액', color='그룹', barmode='group',
                              title="요일별 총 매출 합계", text_auto='.2s')
        st.plotly_chart(fig_day_rev, use_container_width=True)
    with c2:
        fig_day_sel = px.line(weekday_stats, x='요일', y='셀러명', color='그룹', markers=True,
                               title="요일별 활동 셀러 수 (공급 밀도)")
        st.plotly_chart(fig_day_sel, use_container_width=True)

    # 2. 셀러당 평균 생산성 (활동 대비 수익성)
    st.write("#### 2️⃣ 셀러당 평균 매출 생산성 (셀러 수가 많아지는 것이 유리한가?)")
    weekday_stats['인당매출'] = weekday_stats['실결제 금액'] / weekday_stats['셀러명']
    fig_prod = px.area(weekday_stats, x='요일', y='인당매출', color='그룹', 
                        title="요일별 셀러 1인당 평균 기여 매출",
                        labels={'인당매출': '평균 매출(원/명)'})
    st.plotly_chart(fig_prod, use_container_width=True)

    st.markdown("---")

    # 3. 채널별 AOV 및 파레토 분석 (VIP 채널/셀러 식별)
    st.write("#### 3️⃣ 채널별 건당 결제액(AOV) 및 매출 기여도")
    col_p1, col_p2 = st.columns(2)
    
    with col_p1:
        # 채널별 AOV
        ch_aov = f_df.groupby('주문경로')['실결제 금액'].mean().sort_values(ascending=False).reset_index()
        fig_aov = px.bar(ch_aov, x='실결제 금액', y='주문경로', orientation='h', color='실결제 금액',
                          title="채널별 건당 평균 결제액(AOV)", text_auto='.0f')
        st.plotly_chart(fig_aov, use_container_width=True)
        
    with col_p2:
        # 셀러 매출 파레토 (상위 20%가 80%를 만드는가?)
        sel_contri = f_df.groupby('셀러명')['실결제 금액'].sum().sort_values(ascending=False).reset_index()
        sel_contri['누적매출비중'] = (sel_contri['실결제 금액'].cumsum() / sel_contri['실결제 금액'].sum()) * 100
        sel_contri['셀러순위비중'] = (sel_contri.index + 1) / len(sel_contri) * 100
        
        fig_pareto = px.line(sel_contri, x='셀러순위비중', y='누적매출비중',
                              title="셀러 매출 기여도(파레토 곡선)",
                              labels={'셀러순위비중': '셀러 상위 %', '누적매출비중': '누적 매출 비중(%)'})
        fig_pareto.add_hline(y=80, line_dash="dot", annotation_text="80% 매출 지점")
        st.plotly_chart(fig_pareto, use_container_width=True)

    # 4. 신규 vs 재구매 매출 추이 (성장 동력 진단)
    st.write("#### 4️⃣ 신규 vs 재구매 매출 비중 추이 (성장의 질 분석)")
    f_df['고객유형'] = f_df['재구매 횟수'].apply(lambda x: '재구매 고객' if x > 0 else '신규 고객')
    type_trend = f_df.groupby(['주문날짜', '고객유형'])['실결제 금액'].sum().reset_index()
    fig_type = px.area(type_trend, x='주문날짜', y='실결제 금액', color='고객유형',
                        title="일자별 신규 vs 재구매 매출 구성 추이")
    st.plotly_chart(fig_type, use_container_width=True)

    # 5. 채널 성과 요약 표
    st.subheader("📝 채널별 성과 지표 요약 (Raw Data)")
    ch_sum = f_df.groupby('주문경로').agg({
        '실결제 금액': 'sum',
        '주문번호': 'count',
        '재구매여부': lambda x: x.mean() * 100
    }).rename(columns={'실결제 금액': '매출', '주문번호': '건수', '재구매여부': '재구매비중(%)'}).reset_index()
    st.dataframe(ch_sum.sort_values(by='매출', ascending=False), hide_index=True, use_container_width=True)

    # 마케팅 전략 제언 섹션 추가
    st.markdown("---")
    with st.expander("💡 **요일별 셀러 집중 시 마케팅 전략 제언**", expanded=True):
        st.info("""
        특정 요일에 셀러와 상품이 집중될 경우, 마케터는 다음과 같은 입체적인 전략을 구사할 수 있습니다.

        1. **경쟁 밀도 기반 구매 전환 강화 (FOMO 전략)**
           - 셀러가 몰리는 요일은 고객 유입량도 많을 가능성이 높습니다. 
           - **'오늘만 이 가격'**, **'현재 OOO명 구매 중'** 등 실시간 활동성 데이터를 강조하여 고객의 빠른 의사결정을 유도하세요.

        2. **광고 예산 집행 최적화 (Bidding 전략)**
           - 경쟁 셀러가 많은 요일은 키워드 광고 단가(CPC)가 상승합니다. 
           - 오히려 셀러 활동이 적은 '비수기 요일'에 **'틈새 타임 특가'**를 운영하여 저렴한 비용으로 노출을 확보하는 역발상 전략이 필요합니다.

        3. **물류 부하 분산 및 고객 경험 관리 (SCM 연계)**
           - 특정 요일 주문 폭주일 경우 배송 지연이 발생할 수 있습니다. 
           - **'예약 구매 시 추가 포인트'** 또는 **'주말 집하 시 무료 배송'** 등의 혜택을 제공하여 주문을 분산시키고 서비스 품질을 유지하세요.
        """)


# --- 탭 2: 셀러 & 로열티 ---
with tab2:
    st.subheader("인기 품종 및 로열티 셀러 분석 (그래프 4, 5)")
    c3, c4 = st.columns(2)
    with c3:
        # [그래프 4] 품종별 판매량
        prod_count = f_df['품종'].value_counts().head(10).reset_index()
        fig4 = px.bar(prod_count, x='품종', y='count', color='품종', title="판매량 상위 품종")
        st.plotly_chart(fig4, use_container_width=True)
    with c4:
        # [그래프 5] 셀러별 매출 상위
        sel_rev = f_df.groupby('셀러명')['실결제 금액'].sum().nlargest(15).reset_index()
        fig5 = px.bar(sel_rev, x='실결제 금액', y='셀러명', orientation='h', color='실결제 금액', title="매출 상위 셀러")
        st.plotly_chart(fig5, use_container_width=True)

    st.markdown("---")
    # --- [개편] 감귤 구매 목적별 옵션 클러스터링 ---
    st.subheader("🍊 감귤 구매 목적별 선호 옵션 비교 (선물 vs 개인소비)")
    st.markdown("고객의 구매 목적에 따라 선호하는 과일의 크기, 무게, 가격대가 극명하게 갈립니다. 이를 통해 타겟별 맞춤 전략을 제안합니다.")
    
    citrus_df = f_df[f_df['품종'] == '감귤'].copy()
    
    if not citrus_df.empty:
        purpose_opt = st.radio("분석 기준 선택", ["과수 크기 선호도", "무게 및 가격대 분포"], horizontal=True)
        
        if purpose_opt == "과수 크기 선호도":
            # 목적별 크기 선호도 비교 (Grouped Bar)
            size_purpose = citrus_df.groupby(['구매목적', '과수 크기']).size().reset_index(name='주문건수')
            fig_size_p = px.bar(size_purpose, x='과수 크기', y='주문건수', color='구매목적', barmode='group',
                                title="구매 목적에 따른 감귤 크기(Size) 선호도",
                                color_discrete_map={'선물용': '#EF553B', '개인소비용': '#636EFA'})
            st.plotly_chart(fig_size_p, use_container_width=True)
            
        else:
            # 목적별 무게 및 가격대 분포 (Grouped Bar)
            st.write("#### ⚖️ 무게 및 가격대별 시장 규모 비교")
            c_dist1, c_dist2 = st.columns(2)
            
            with c_dist1:
                # 1. 무게별 분포
                weight_p = citrus_df.groupby(['구매목적', '무게 구분']).size().reset_index(name='주문건수')
                fig_weight_p = px.bar(weight_p, x='무게 구분', y='주문건수', color='구매목적', barmode='group',
                                      title="구매 목적별 선호 무게(kg) 비교",
                                      color_discrete_map={'선물용': '#EF553B', '개인소비용': '#636EFA'},
                                      text_auto=True)
                st.plotly_chart(fig_weight_p, use_container_width=True)
                
            with c_dist2:
                # 2. 가격대별 분포
                price_p = citrus_df.groupby(['구매목적', '가격대']).size().reset_index(name='주문건수')
                # 가격대 정렬 (가능한 경우)
                fig_price_p = px.bar(price_p, x='가격대', y='주문건수', color='구매목적', barmode='group',
                                     title="구매 목적별 선호 가격대 비교",
                                     color_discrete_map={'선물용': '#EF553B', '개인소비용': '#636EFA'},
                                     text_auto=True)
                st.plotly_chart(fig_price_p, use_container_width=True)

        # 목적별 요약 인사이트 표
        st.write("**� 구매 목적별 베스트 옵션 요약**")
        summary_p = citrus_df.groupby('구매목적').agg({
            '실결제 금액': 'mean',
            '무게 구분': lambda x: x.mode()[0] if not x.mode().empty else 'N/A',
            '과수 크기': lambda x: x.mode()[0] if not x.mode().empty else 'N/A'
        }).rename(columns={'실결제 금액': '평균 객단가', '무게 구분': '가장 많이 팔린 무게', '과수 크기': '대표 선호 크기'}).reset_index()
        
        st.table(summary_p)
        
        st.info("""
        **💡 목적별 마케팅 포인트**
        - **선물용**: 가격 저항선이 낮으므로 **'프리미엄 로얄과'**와 **'고급 포장'**을 강조한 고단가 세트 구성에 집중하세요.
        - **개인소비용**: 가성비가 최우선입니다. **'못난이/가정용'** 키워드와 함께 **10kg 대용량** 벌크 상품의 가격 경쟁력을 확보하는 것이 유리합니다.
        """)
    else:
        st.warning("데이터 내 '감귤' 품종에 대한 상세 정보가 부족합니다.")
    st.markdown("---")


    st.subheader("🏅 로열티 지표 요약 (표 2, 3)")
    c5, c6 = st.columns(2)
    with c5:
        # [표 2] 매출 상위 셀러
        st.write("**매출 상위 10개 셀러**")
        st.dataframe(sel_rev.head(10), use_container_width=True)
    with c6:
        # [표 3] 재구매율 높은 셀러 (30건 이상)
        st.write("**재구매 로열티가 높은 셀러**")
        counts = f_df.groupby('셀러명').size()
        repeats = f_df[f_df['재구매여부'] == True].groupby('셀러명').size()
        r_ratio = (repeats / counts * 100).fillna(0).loc[counts[counts>=30].index].nlargest(10).reset_index()
        r_ratio.columns = ['셀러명', '재구매율(%)']
        st.dataframe(r_ratio, use_container_width=True)


# --- 탭: 상품 페이지 분석 (신규) ---
with tab_prod:
    st.subheader("📦 상품 페이지별 매출 기여도 및 옵션 분석")
    st.markdown("""
    매출 상위 5개 상품 페이지를 추출하고, 해당 페이지가 **킹댕즈**와 관련된 페이지인지 아니면 **일반 셀러**들이 경쟁하는 페이지인지를 구분하여 분석합니다.
    """)

    # 상품페이지(상품명)별 통계 계산
    # 셀러명에 NaN이 있을 경우 sorted()에서 에러가 발생하므로 dropna()와 문자열 변환 처리
    page_stats = f_df.groupby('상품명').agg({
        '실결제 금액': 'sum',
        '주문번호': 'count',
        '셀러명': lambda x: sorted(list(set(x.dropna().astype(str))))
    }).reset_index()
    
    # 페이지 유형 분류 (킹댕즈 참여 여부)
    def classify_page(sellers):
        if '킹댕즈' in sellers:
            return '킹댕즈 참여 페이지'
        else:
            return '일반셀러 경쟁 페이지'
    
    page_stats['페이지 유형'] = page_stats['셀러명'].apply(classify_page)
    top5_pages = page_stats.nlargest(5, '실결제 금액')

    # 시각화: Top 5 페이지 매출
    fig_top_page = px.bar(top5_pages, x='실결제 금액', y='상품명', color='페이지 유형',
                          orientation='h', title="매출 상위 5개 상품 페이지 (Revenue Top 5)",
                          labels={'실결제 금액': '총 매출액(원)', '상품명': '상품 페이지명'},
                          color_discrete_map={'킹댕즈 참여 페이지': '#FF4B4B', '일반셀러 경쟁 페이지': '#1C83E1'})
    fig_top_page.update_layout(yaxis={'categoryorder':'total ascending'}) # 매출 높은 순 정렬
    st.plotly_chart(fig_top_page, use_container_width=True)

    st.write("### 🔍 Top 5 페이지 상세 옵션 & 셀러 분석")
    st.info("각 페이지를 클릭하면 해당 페이지에서 가장 많이 팔린 품종, 크기, 무게 옵션과 판매 셀러 현황을 볼 수 있습니다.")
    
    for i, (idx, row) in enumerate(top5_pages.iterrows()):
        p_name = row['상품명']
        with st.expander(f"🏆 Top {i+1}: [{row['페이지 유형']}] {p_name[:60]}...", expanded=(i==0)):
            p_df = f_df[f_df['상품명'] == p_name]
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.write("**🍎 품종 및 크기 조합**")
                opt_size = p_df.groupby(['품종', '과수 크기']).size().reset_index(name='주문건수')
                st.dataframe(opt_size.sort_values('주문건수', ascending=False), hide_index=True, use_container_width=True)
            with c2:
                st.write("**⚖️ 무게 및 가격대 분포**")
                opt_weight = p_df.groupby(['무게 구분', '가격대']).size().reset_index(name='주문건수')
                st.dataframe(opt_weight.sort_values('주문건수', ascending=False), hide_index=True, use_container_width=True)
            with c3:
                st.write("**👤 판매 셀러 현황**")
                opt_seller = p_df.groupby('셀러명').agg({'실결제 금액':'sum', '주문번호':'count'}).reset_index()
                opt_seller.columns = ['셀러명', '매출액', '주문건수']
                st.dataframe(opt_seller.sort_values('매출액', ascending=False), hide_index=True, use_container_width=True)

    st.markdown("---")
    st.success("""
    **💡 상품 페이지 차별화 전략 인사이트**
    1. **킹댕즈 참여 페이지**: 브랜드 신뢰도를 바탕으로 **'선물용'**이나 **'고급 규격(로얄과)'** 옵션에서 압도적인 전환율을 보입니다. 
    2. **일반셀러 경쟁 페이지**: 여러 셀러가 동일 페이지에서 판매하므로 **'가격 경쟁력'**과 **'가성비(대용량/가정용)'** 옵션이 매출의 핵심 동력입니다.
    3. **성공 공식 전이**: 매출 1위 페이지의 인기 옵션(예: 5kg/2-3만원대/로얄과)을 파악하여, 신규 상품 페이지 구성 시 해당 옵션을 **'메인 랜딩 옵션'**으로 배치하는 전략이 필요합니다.
    """)


    st.markdown("---")


# --- 탭: 재구매 퍼널 & 패턴 (신규) ---
with tab_funnel:
    st.subheader("🔁 고객 재구매 퍼널 및 행동 패턴 분석")
    st.markdown("""
    고객이 첫 구매 이후 얼마나 다시 돌아오는지, 그리고 재방문 시 어떤 행동 변화를 보이는지 분석하여 **리텐션(Retention) 전략**을 제안합니다.
    """)

    # 1. 구매 회차별 퍼널 (Retention Funnel Report)
    st.write("#### 1️⃣ 구매 회차별 고객 전환 리포트 (Retention Funnel)")
    
    # 각 회차별 유니크 고객 수 집계
    funnel_data = f_df.groupby('재구매_날짜순서')['주문자연락처'].nunique().reset_index()
    funnel_data.columns = ['단계', '고객수']
    
    # 지표 계산: 잔존율(첫구매 대비), 전환율(전단계 대비)
    first_purchase_count = funnel_data.iloc[0]['고객수']
    funnel_data['잔존율(%)'] = (funnel_data['고객수'] / first_purchase_count * 100).round(1)
    
    # 전단계 대비 전환율 (pct_change와 유사하게 계산)
    funnel_data['전단계 대비 전환율(%)'] = (funnel_data['고객수'] / funnel_data['고객수'].shift(1) * 100).fillna(100).round(1)
    
    # 라벨링
    funnel_data['구매회차'] = funnel_data['단계'].apply(lambda x: f"{int(x)+1}회차 구매자")
    
    # 컬럼 순서 및 이름 정리
    funnel_report = funnel_data[['구매회차', '고객수', '잔존율(%)', '전단계 대비 전환율(%)']]
    
    # 스타일링 및 출력
    st.dataframe(funnel_report.style.background_gradient(subset=['잔존율(%)'], cmap='YlGnBu')
                 .format({'고객수': '{:,}명', '잔존율(%)': '{:.1f}%', '전단계 대비 전환율(%)': '{:.1f}%'}),
                 use_container_width=True, hide_index=True)
    
    st.caption("※ 잔존율(%)은 1회차 구매자(신규 유입) 대비 해당 회차까지 살아남은 고객의 비중입니다.")

    # 시각화 차트 추가 (깔때기 및 잔존율 곡선)
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        fig_f_chart = px.funnel(funnel_data, x='고객수', y='구매회차', 
                                title="고객 잔존 깔때기 (Funnel Shape)",
                                color_discrete_sequence=['#636EFA'])
        st.plotly_chart(fig_f_chart, use_container_width=True)
    
    with col_v2:
        fig_r_chart = px.line(funnel_data, x='구매회차', y='잔존율(%)', markers=True,
                              title="회차별 잔존율 추세 (Retention Curve)",
                              text='잔존율(%)')
        fig_r_chart.update_traces(textposition="top center")
        st.plotly_chart(fig_r_chart, use_container_width=True)

    st.markdown("---")

    c_f1, c_f2 = st.columns(2)
    
    with c_f1:
        # 2. 재구매 주기 분석 (Repurchase Interval)
        st.write("#### 2️⃣ 평균 재구매 주기 및 분포")
        # 고객별 주문 간격 계산
        f_df_sorted = f_df.sort_values(['주문자연락처', '주문일'])
        f_df_sorted['이전주문일'] = f_df_sorted.groupby('주문자연락처')['주문날짜'].shift(1)
        # pd.to_datetime 이 이미 되어있으므로 날짜 차이 계산
        f_df_sorted['구매간격'] = (pd.to_datetime(f_df_sorted['주문날짜']) - pd.to_datetime(f_df_sorted['이전주문일'])).dt.days
        
        # 이전 구매가 있는 (재구매인) 건들만 대상으로 주기 계산
        intervals = f_df_sorted[f_df_sorted['구매간격'] > 0]['구매간격']
        
        if not intervals.empty:
            avg_interval = intervals.mean()
            st.metric("평균 재구매 주기", f"{avg_interval:.1f}일")
            
            fig_interval = px.histogram(intervals, x='구매간격', 
                                        nbins=30, title="재구매 소요 기간 분포 (Days)",
                                        labels={'구매간격': '소요 기간(일)', 'count': '주문 건수'})
            st.plotly_chart(fig_interval, use_container_width=True)
        else:
            st.info("재구매 데이터가 부족하여 주기를 산출할 수 없습니다.")

    with c_f2:
        # 3. 회차별 평균 결제 금액 (AOV Progression)
        st.write("#### 3️⃣ 구매 회차별 평균 객단가(AOV) 변화")
        order_aov = f_df.groupby('재구매_날짜순서')['실결제 금액'].mean().reset_index()
        order_aov['구매회차'] = order_aov['재구매_날짜순서'] + 1
        
        fig_aov_trend = px.line(order_aov, x='구매회차', y='실결제 금액', markers=True,
                                title="구매 회차가 거듭될수록 결제액이 변하는가?",
                                labels={'실결제 금액': '평균 결제액(원)', '구매회차': '구매 회차'})
        st.plotly_chart(fig_aov_trend, use_container_width=True)

    st.markdown("---")
    
    # 4. 품종 확장 패턴 (Cross-sell)
    st.write("#### 4️⃣ 재구매 시 품종 탐색 및 확장 패턴")
    
    first_counts = f_df[f_df['재구매_날짜순서'] == 0]['품종'].value_counts(normalize=True).head(5).reset_index()
    repeat_counts = f_df[f_df['재구매_날짜순서'] > 0]['품종'].value_counts(normalize=True).head(5).reset_index()
    first_counts.columns = ['품종', '비중']
    repeat_counts.columns = ['품종', '비중']
    first_counts['유형'] = '첫 구매'
    repeat_counts['유형'] = '재구매'
    
    cross_df = pd.concat([first_counts, repeat_counts])
    fig_cross = px.bar(cross_df, x='비중', y='품종', color='유형', barmode='group',
                       title="첫 구매 vs 재구매 시 주요 품종 선호도 비교",
                       orientation='h')
    st.plotly_chart(fig_cross, use_container_width=True)

    st.success("""
    **💡 재구매 극대화를 위한 마케팅 액션 아이템**
    1. **이탈 방지 구간 타겟팅**: 퍼널 차트에서 급격히 숫자가 줄어드는 구간(예: 2회->3회) 직후에 **'강력한 리워드'**를 배치하세요.
    2. **최적의 리마인드 시점**: 평균 재구매 주기가 확인되었습니다. 고객의 마지막 구매일로부터 **평균 주기 직전**에 맞춤형 할인 코드를 푸시하세요.
    3. **카테고리 믹스 전략**: 첫 구매 시 '감귤'만 사던 고객이 재구매 시 다른 품목으로 확장되지 않는다면, **'합배송 할인'**이나 **'맛보기 샘플'**을 통해 품종 확장을 유도해야 합니다.
    """)


# --- 탭 3: 지역별 분석 ---
with tab3:
    st.subheader("🗺️ 지역별 입체 분석 및 전략적 클러스터링")
    st.markdown("전국 지역별 매출 분포와 주문 경로, 셀러 간의 상관관계를 한눈에 파악할 수 있도록 시각화하였습니다.")

    # 1. 시각적 클러스터링: 매출 vs 재구매율 (지역 성격 분류)
    st.subheader("1. 지역별 성격 분류 (매출 규모 vs 재구매 로열티)")
    
    reg_stats = f_df.groupby('광역지역(정식)').agg({
        '실결제 금액': 'sum',
        '재구매여부': lambda x: x.mean() * 100,
        '주문번호': 'count'
    }).reset_index()
    reg_stats.columns = ['지역', '총매출', '재구매율', '주문건수']
    
    fig_reg_cluster = px.scatter(reg_stats, x='총매출', y='재구매율', size='주문건수', color='지역',
                                 text='지역', title="지역별 매출-로열티 클러스터 현황",
                                 labels={'총매출': '총 매출액(원)', '재구매율': '재구매 비중(%)'})
    # 평균선 추가 (클러스터 구분선)
    fig_reg_cluster.add_hline(y=reg_stats['재구매율'].mean(), line_dash="dot", annotation_text="평균 재구매율")
    fig_reg_cluster.add_vline(x=reg_stats['총매출'].mean(), line_dash="dot", annotation_text="평균 매출액")
    st.plotly_chart(fig_reg_cluster, use_container_width=True)
    
    st.info("""
    **[클러스터 해석 가이드]**
    - **우상단 (Star)**: 매출도 높고 재구매도 활발한 핵심 공략 지역
    - **우하단 (Growth)**: 매출은 높으나 재구매가 낮은 신규 유입 중심 지역
    - **좌상단 (Loyalty)**: 매출 규모는 작으나 충성도가 높은 알짜 지역
    """)

    st.markdown("---")

    # 2. 계층형 분석: 지역 > 경로 > 셀러 (Sunburst)
    st.subheader("2. 상위 지역별 유입 경로 및 셀러 계층 구조 (Top 5 지역)")
    top5_regions = reg_stats.nlargest(5, '총매출')['지역'].tolist()
    hierarchy_df = f_df[f_df['광역지역(정식)'].isin(top5_regions)].copy()
    
    # 데이터 안정성 확보: 결측치 처리 및 사전 집계
    path_cols = ['광역지역(정식)', '주문경로', '셀러명']
    for col in path_cols:
        hierarchy_df[col] = hierarchy_df[col].fillna(f"{col} 정보없음")
    
    # Plotly Sunburst 오류 방지를 위해 명시적 집계 수행
    sunburst_df = hierarchy_df.groupby(path_cols)['실결제 금액'].sum().reset_index()
    sunburst_df = sunburst_df[sunburst_df['실결제 금액'] > 0] # 0이하 값 제거
    
    fig_sunburst = px.sunburst(sunburst_df, path=path_cols, 
                                values='실결제 금액', title="지역-경로-셀러 매출 비중 계층도",
                                color='광역지역(정식)', color_discrete_sequence=px.colors.qualitative.Pastel)
    st.plotly_chart(fig_sunburst, use_container_width=True)

    st.markdown("---")

    # 3. 통합 요약표: 전국 지역별 '최강 조합' 한눈에 보기
    st.subheader("3. 🏆 전국 지역별 베스트 [경로 x 셀러] 통합 리포트")
    
    # 지역별로 가장 매출이 높은 경로x셀러 조합 추출
    best_combi_all = f_df.groupby(['광역지역(정식)', '주문경로', '셀러명'])['실결제 금액'].sum().reset_index()
    idx = best_combi_all.groupby('광역지역(정식)')['실결제 금액'].idxmax()
    best_combi_summary = best_combi_all.loc[idx].sort_values(by='실결제 금액', ascending=False)
    best_combi_summary.columns = ['지역', '베스트 경로', '베스트 셀러', '매출합계']
    
    st.dataframe(best_combi_summary.style.background_gradient(subset=['매출합계'], cmap='Blues'),
                 use_container_width=True, hide_index=True)

    # 4. 상세 조회 (기존 기능 강화)
    with st.expander("🔍 특정 지역 상세 데이터 조회"):
        sel_reg = st.selectbox("상세 분석할 지역 선택", options=reg_stats['지역'].tolist())
        c_reg1, c_reg2 = st.columns(2)
        
        reg_df_detail = f_df[f_df['광역지역(정식)'] == sel_reg]
        
        with c_reg1:
            st.write(f"**[{sel_reg}] 경로별 기여도**")
            path_pie = px.pie(reg_df_detail, values='실결제 금액', names='주문경로', hole=0.3)
            st.plotly_chart(path_pie, use_container_width=True)
        
        with c_reg2:
            st.write(f"**[{sel_reg}] 상위 셀러 Top 5**")
            top_sel_bar = px.bar(reg_df_detail.groupby('셀러명')['실결제 금액'].sum().nlargest(5).reset_index(),
                                 x='실결제 금액', y='셀러명', orientation='h', color='실결제 금액')
            st.plotly_chart(top_sel_bar, use_container_width=True)

    st.markdown("---")


# --- 탭: 구매 시점 분석 (신규) ---
with tab_time:
    st.subheader("⏰ 소비자 구매 요일/시간 패턴 분석 (Clustering)")
    st.markdown("""
    소비자들의 구매 패턴을 요일과 시간대를 기준으로 **4개의 클러스터**로 분류했습니다. 
    가장 주문이 집중되는 골든 타임을 파악하여 마케팅 푸시 및 광고 집행 시점을 최적화하세요.
    """)

    # 1. 클러스터별 요약 테이블 (사용자 요청 포맷)
    st.write("#### 📋 구매 패턴 클러스터링 요약")
    
    # 요일 이름 매핑용
    day_map = {0:'월요일', 1:'화요일', 2:'수요일', 3:'목요일', 4:'금요일', 5:'토요일', 6:'일요일'}
    
    cluster_stats = f_df.groupby('time_cluster').agg({
        '주문번호': 'count',
        '실결제 금액': 'mean',
        '주문일': lambda x: x.dt.dayofweek.mode()[0],
        'time_cluster': 'first' # 해석을 위해
    }).reset_index(drop=True)
    
    # 대표 시간(최빈값) 추가
    cluster_stats['대표시간'] = f_df.groupby('time_cluster')['주문일'].apply(lambda x: f"{x.dt.hour.mode()[0]}시")
    
    # 해석 및 정리
    meaning_map = {
        1: '평일 오후 피크',
        2: '주말 저녁 피크',
        0: '새벽 저강도 (주말)',
        3: '새벽 저강도 (평일)'
    }
    cluster_stats['해석'] = cluster_stats['time_cluster'].map(meaning_map)
    cluster_stats['대표요일'] = cluster_stats['주문일'].map(day_map)
    cluster_stats.columns = ['cluster', '총 주문수', '평균주문금액', '요일번호', '대표시간', '해석', '대표요일']
    
    # 최종 출력용 정렬 및 선택
    disp_table = cluster_stats[['cluster', '총 주문수', '평균주문금액', '대표요일', '대표시간', '해석']]
    st.dataframe(disp_table.sort_values('총 주문수', ascending=False), hide_index=True, use_container_width=True)

    st.markdown("---")

    # 2. 요일 x 시간 히트맵
    st.write("#### 📅 요일 × 시간대별 주문 집중도 히트맵")
    
    # 히트맵 데이터 생성
    f_df['hour'] = f_df['주문일'].dt.hour
    f_df['day_name'] = f_df['주문일'].dt.day_name()
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    pivot_df = f_df.groupby(['day_name', 'hour']).size().unstack(fill_value=0)
    pivot_df = pivot_df.reindex(day_order) # 요일 순서 정렬
    
    fig_heatmap = px.imshow(pivot_df, 
                            labels=dict(x="시간(Hour)", y="요일(Day)", color="주문건수"),
                            x=list(range(24)),
                            y=day_order,
                            color_continuous_scale='Viridis',
                            title="요일별 시간대 주문 발생 현황 (Heatmap)")
    st.plotly_chart(fig_heatmap, use_container_width=True)

    st.info("""
    **💡 마케팅 시점 인사이트**
    - **피크 타임(Cluster 1, 2)**: 주문이 가장 몰리는 시간입니다. **실시간 베스트 상품** 노출과 **타임 세일** 종료 임박 알림을 통해 구매 전환을 극대화하세요.
    - **저강도 시간(Cluster 0, 3)**: 주문은 적지만 평온한 새벽 시간입니다. **예약 발송 푸시**를 설정하여 고객이 잠에서 깨어나는 아침 8~9시에 첫 알람을 받도록 설계하세요.
    """)


# --- 탭: 등급별 분석 (신규) ---
with tab_grade:
    st.subheader("💎 상품 등급 및 구매 목적별 입체 분석")
    st.markdown("""
    상품 등급(프리미엄/일반)과 구매 목적(선물용/자기소비용)을 결합하여 **수익성**과 **고객 선호도**를 분석합니다.
    """)

    # 정확한 AOV 계산을 위한 함수 (주문번호 기준)
    def calculate_true_aov(data, group_col):
        stats = data.groupby(group_col).agg({
            '실결제 금액': 'sum',
            '주문번호': 'nunique'
        }).reset_index()
        stats['AOV'] = stats['실결제 금액'] / stats['주문번호']
        return stats

    # 1. 등급 vs 목적 교차 분석
    st.write("#### 1️⃣ 상품 등급 및 구매 목적별 지표")
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        # 등급별 AOV
        grade_aov = calculate_true_aov(f_df, '상품성등급_그룹')
        fig_g_aov = px.bar(grade_aov, x='상품성등급_그룹', y='AOV', color='상품성등급_그룹',
                            title="상품 등급별 평균 객단가(AOV)", text_auto='.0f',
                            color_discrete_map={'프리미엄': '#FFD700', '일반': '#C0C0C0'})
        st.plotly_chart(fig_g_aov, use_container_width=True)
    
    with col_g2:
        # 목적별 AOV
        purpose_aov = calculate_true_aov(f_df, '구매목적')
        fig_p_aov = px.bar(purpose_aov, x='구매목적', y='AOV', color='구매목적',
                            title="구매 목적별 평균 객단가(AOV)", text_auto='.0f',
                            color_discrete_map={'선물용': '#EF553B', '자기소비용': '#636EFA'})
        st.plotly_chart(fig_p_aov, use_container_width=True)

    st.warning("""
    **❓ 왜 '프리미엄'이나 '선물용'의 객단가가 더 낮거나 비등하게 보이나요?**
    - **단위 무게의 차이**: '일반/자기소비용' 상품은 주로 **10kg 대용량 벌크**로 구매하는 경우가 많아 단일 주문 금액이 큽니다(예: 4~5만원대). 
    - **프리미엄의 특성**: 반면 '프리미엄/선물용'은 퀄리티는 높지만 **3kg~5kg 내외의 정제된 소포장**이 주를 이루어, 건당 결제 금액은 대용량 일반 상품보다 낮게 형성될 수 있습니다.
    - **결론**: 프리미엄은 **'마진율(kg당 단가)'**에서 승부하고, 일반은 **'물량 및 총 매출액'**에서 승부하는 구조임을 데이터가 보여줍니다.
    """)

    st.markdown("---")

    # 2. 목적별 재구매 패턴
    st.write("#### 2️⃣ 구매 목적에 따른 재구매 충성도")
    purpose_stats = f_df.groupby('구매목적').agg({
        '재구매여부': 'mean',
        '주문번호': 'count'
    }).reset_index()
    purpose_stats['재구매비중'] = purpose_stats['재구매여부'] * 100

    fig_p_rep = px.bar(purpose_stats, x='구매목적', y='재구매비중', color='구매목적',
                        title="선물용 vs 자기소비용 재구매율 비교", text_auto='.1f',
                        color_discrete_map={'선물용': '#EF553B', '자기소비용': '#636EFA'})
    st.plotly_chart(fig_p_rep, use_container_width=True)

    st.info("""
    **💡 목적별 마케팅 인사이트 (Data-Driven)**
    - **선물용 (Gift) - [충성도 고집단]**: 예상과 달리 선물용 고객의 재구매율이 **33.9%**로 자기소비용보다 훨씬 높습니다. 이는 "검증된 품질"에 대한 신뢰가 형성된 고객이 다른 지인이나 다음 명절에도 우리 서비스를 다시 찾는 **'프리미엄 반복 구매'** 특성을 보이기 때문입니다. 
      - **전략**: 선물 이력을 관리하여 명절이나 기념일 직전에 **'작년 그 상품'** 리마인드 마케팅을 진행하는 것이 매우 효과적입니다.
    - **자기소비용 (Self-Consumption) - [신규 유입 중심]**: 재구매율이 **24.8%**로 상대적으로 낮습니다. 일상적인 소비는 가격 비교가 쉽고 타 시장으로의 이탈이 잦기 때문으로 분석됩니다.
      - **전략**: '가성비' 강조만으로는 한계가 있습니다. **'정기 구독'**이나 **'멤버십 포인트'** 제도를 도입하여 고정적인 재방문 유인(Lock-in)을 만들어야 합니다.
    """)




with tab4:
    st.subheader("기타/크롬 경로 상세 분석 (표 5)")
    detail_paths = f_df[f_df['주문경로'].isin(['기타', '크롬'])]
    
    # [표 5] 신규 vs 기존 유입 분석
    st.write("**신규 유입 고객 vs 기존 고객 재방문 비중**")
    detail_paths['유형'] = detail_paths['재구매여부'].apply(lambda x: '기존' if x else '신규')
    path_summary = detail_paths.groupby(['주문경로', '유형']).size().unstack(fill_value=0)
    st.table(path_summary)

    # [그래프 7] 회원/비회원 구분
    st.write("**회원 vs 비회원 구매 비중**")
    mem_dist = detail_paths.groupby(['주문경로', '회원구분']).size().reset_index(name='건수')
    fig7 = px.bar(mem_dist, x='주문경로', y='건수', color='회원구분', barmode='group')
    st.plotly_chart(fig7, use_container_width=True)

# --- 탭: 셀러 성장 전략 (신규) ---
# --- 탭: 셀러 성장 전략 (보고서 형식) ---
with tab_growth:
    st.header("📋 셀러 성장 및 인플루언서 영입 전략 보고서")
    
    # 1. 목적
    st.markdown("### 1. 목적")
    st.info("본 보고서는 쇼핑몰의 지속 가능한 성장을 위해 현재 안정적인 매출을 담당하는 **'지인 기반 셀러'**를 정예화하고, 폭발적인 확장이 가능한 **'제2의 킹댕즈(인플루언서)'**를 발굴 및 영입하기 위한 데이터 기반 전략 도출을 목적으로 함.")

    # 2. 결론
    st.markdown("### 2. 결론")
    st.success("""
    - **통합 운영 전략**: 일반 셀러의 '안정적 리텐션'과 인플루언서의 '신규 유입력'을 상호 보완적으로 운영해야 함.
    - **인플루언서 영입**: 제주 지표에 특화된 프리미엄 상품군과 SNS용 콘텐츠 소스를 지원하여 인플루언서의 활동 명분을 강화해야 함.
    - **보상 체계**: 단순 판매 수수료를 넘어 '신규 고객 유치 인센티브' 도입을 통해 플랫폼의 확장을 유도해야 함.
    """)

    # 3. 배경
    st.markdown("### 3. 배경")
    st.markdown("""
    - **성장 정체**: 현재 매출의 상당 부분이 지인 기반의 소규모 판매에 머물러 있어, 플랫폼 외부에서의 대규모 신규 유입이 절실함.
    - **높은 의존도**: 1등 셀러(인플루언서)의 단발성 판매 시점에만 매출이 급증하는 현상이 반복되어, 지속적인 스파이크를 만들어낼 인플루언서 풀(Pool) 확보가 과제임.
    """)

    # 4. 정의
    st.markdown("### 4. 정의")
    col_def1, col_def2 = st.columns(2)
    with col_def1:
        st.write("**[안정형] 일반 셀러**")
        st.caption("카카오톡 등 지인 기반 채널을 통해 충성도 높은 단골 고객 위주로 판매하는 셀러")
    with col_def2:
        st.write("**[폭발형] 인플루언서(킹댕즈)**")
        st.caption("강력한 팬덤과 SNS 파급력을 바탕으로 외부 신규 고객을 단기간에 플랫폼으로 전이시키는 셀러")

    # 5. 산출방식
    st.markdown("### 5. 산출방식")
    st.markdown("""
    - **채널 기여도**: 주문 데이터에서 추출한 원본 `주문경로`를 셀러 그룹별로 비중 분석.
    - **고객 획득**: 신규 고객 vs. 재구매 고객의 비중을 통해 셀러의 '새 피 수혈' 능력 측정.
    - **매출 패턴**: 시계열 데이터를 활용한 매출 스파이크 지점 및 지속 기간 분석.
    - **상품 적합도**: 각 그룹별 평균 객단가(AOV) 및 프리미엄 상품 판매 비중 교차 분석.
    """)

    st.markdown("---")

    # 6. 분석결과
    st.markdown("### 6. 분석결과")

    # 6-1. 유입 경로 비교
    st.subheader("📊 6-1. 상세 유입 경로 분석 (안정성 vs. 확장성)")
    channel_comp = f_df.groupby(['그룹', '주문경로']).size().reset_index(name='주문건수')
    group_totals = channel_comp.groupby('그룹')['주문건수'].transform('sum')
    channel_comp['비중(%)'] = (channel_comp['주문건수'] / group_totals * 100).round(1)
    
    channel_pivot = channel_comp.pivot(index='주문경로', columns='그룹', values='비중(%)').fillna(0)
    st.write("**[상세 데이터] 유입 경로별 비중 (%)**")
    st.dataframe(channel_pivot.style.format("{:.1f}%").background_gradient(axis=0, cmap='YlGnBu'), use_container_width=True)
    
    channel_comp['레이블'] = channel_comp['주문경로'] + ": " + channel_comp['비중(%)'].astype(str) + "%"
    fig_chan_comp = px.bar(channel_comp, y='그룹', x='주문건수', color='주문경로',
                            title="일반 셀러 vs 킹댕즈: 유입 경로 비중 분석 (%)",
                            orientation='h', text='레이블')
    fig_chan_comp.update_traces(textposition='inside')
    fig_chan_comp.update_layout(barnorm='percent', xaxis_title="유입 비중 (%)", yaxis_title="셀러 그룹", showlegend=False)
    st.plotly_chart(fig_chan_comp, use_container_width=True)
    
    st.info("""
    **💡 데이터 분석 포인트**
    - **일반 셀러**: 특정 채널에 의존하기보다 다양한 경로를 통해 유입이 분산되어 있어 운영적 안정성이 높음.
    - **킹댕즈**: 특정 SNS 채널을 통한 유입이 절대적이며, 해당 채널의 전파 속도가 성장을 결정함.
    """)

    # 6-2. 신규 고객 유치 기여도 (도넛 그래프)
    st.subheader("📊 6-2. 고객 유형별 기여도 분석 (신규 vs. 재구매)")
    st.markdown("""
    > **💡 지표 정의 안내**
    > - **신규 고객**: 해당 '주문자 연락처'를 기준으로 생애 **첫 번째 주문 날짜**에 발생한 모든 주문.
    > - **재구매 고객**: 첫 주문 발생일 이후, **최소 1일이 경과한 서로 다른 날짜**에 다시 방문하여 결제한 주문.  
    >   *(※ 동일한 날짜 내에 여러 번 주문한 경우, 데이터 정제 기준에 따라 '재구매'가 아닌 '신규/단일 방문' 거래로 분류됨)*
    """)
    
    col_c1, col_c2 = st.columns(2)
    
    with col_c1:
        # 일반 셀러 신규/재구매 비중
        gen_cust = f_df[f_df['그룹'] == '일반 셀러']['고객유형'].value_counts().reset_index()
        gen_cust.columns = ['고객유형', '건수']
        fig_gen_pie = px.pie(gen_cust, values='건수', names='고객유형', hole=0.5,
                              title="일반 셀러: 고객 구성 비율",
                              color_discrete_map={'신규 고객': '#A5D6A7', '재구매 고객': '#1B5E20'})
        fig_gen_pie.update_traces(textinfo='percent+label')
        st.plotly_chart(fig_gen_pie, use_container_width=True)
        
    with col_c2:
        # 킹댕즈 신규/재구매 비중
        kd_cust = f_df[f_df['그룹'] == '킹댕즈']['고객유형'].value_counts().reset_index()
        kd_cust.columns = ['고객유형', '건수']
        fig_kd_pie = px.pie(kd_cust, values='건수', names='고객유형', hole=0.5,
                             title="킹댕즈: 고객 구성 비율",
                             color_discrete_map={'신규 고객': '#FFCDD2', '재구매 고객': '#B71C1C'})
        fig_kd_pie.update_traces(textinfo='percent+label')
        st.plotly_chart(fig_kd_pie, use_container_width=True)
        
    st.warning("**전략 결론**: 도넛 그래프 분석 결과, **킹댕즈**는 외부에서 새로운 고객을 수혈하는 '확장 엔진' 역할을 수행하며, **일반 셀러**는 기존 유입된 고객의 충성도를 유지하는 '안정성' 중심의 구조임이 확인됨.")

    # 6-3. 킹댕즈 매출 스파이크 패턴
    st.subheader("📊 6-3. 인플루언서 매출 폭발 패턴 (Time-series)")
    kd_only = f_df[f_df['그룹'] == '킹댕즈'].copy()
    if not kd_only.empty:
        kd_daily = kd_only.groupby('주문날짜')['실결제 금액'].sum().reset_index()
        fig_spike = px.line(kd_daily, x='주문날짜', y='실결제 금액', markers=True,
                             title="킹댕즈 매출 발생 스파이크",
                             line_shape='spline', color_discrete_sequence=['#FF4B4B'])
        peak_row = kd_daily.loc[kd_daily['실결제 금액'].idxmax()]
        fig_spike.add_annotation(x=peak_row['주문날짜'], y=peak_row['실결제 금액'],
                                 text="SNS 홍보 및 공구 오픈", showarrow=True, arrowhead=1)
        st.plotly_chart(fig_spike, use_container_width=True)
        st.info("인플루언서 판매는 홍보 직후 단기간에 매출이 집중되므로, 이를 체계적으로 반복할 수 있는 '공구 캘린더' 확보가 필수적임.")

    # 6-4. 영입 타겟용 상품 조건 (객단가 집중 분석)
    st.subheader("📊 6-4. 인플루언서 적합 상품 분석 (객단가 중심)")
    
    st.markdown("""
    인플루언서 영입 정당성을 확보하기 위해 가장 중요한 지표는 **객단가(AOV)**입니다. 
    단순히 많이 파는 것을 넘어, '얼마나 비싼 상품을 잘 파는가'가 인플루언서의 가치를 증명합니다.
    """)

    col_aov1, col_aov2 = st.columns([1, 1])
    
    with col_aov1:
        # 그룹별 평균 객단가 (AOV) 바 차트
        group_aov = f_df.groupby('그룹')['실결제 금액'].mean().reset_index()
        fig_aov_bar = px.bar(group_aov, x='그룹', y='실결제 금액', 
                              title="그룹별 평균 객단가(AOV) 비교",
                              text_auto=',.0f',
                              color='그룹', color_discrete_map={'킹댕즈': '#FF4B4B', '일반 셀러': '#1C83E1'})
        fig_aov_bar.update_layout(yaxis_title="평균 결제 금액 (원)")
        st.plotly_chart(fig_aov_bar, use_container_width=True)
        
    with col_aov2:
        # 결제 금액 분포 (Box Plot) - 이상치 제거 혹은 전체 분포 확인
        fig_aov_dist = px.box(f_df, x='그룹', y='실결제 금액', 
                               title="그룹별 주문당 결제 금액 분포",
                               color='그룹', color_discrete_map={'킹댕즈': '#FF4B4B', '일반 셀러': '#1C83E1'},
                               points=False) # 점이 너무 많으면 느려지므로 제외
        fig_aov_dist.update_layout(yaxis_title="결제 금액 (원)")
        st.plotly_chart(fig_aov_dist, use_container_width=True)

    st.success("""
    **💡 분석 결과 및 전략적 시사점**
    - **고단가 소화력**: 킹댕즈와 같은 인플루언서는 일반 셀러 대비 **상대적으로 높은 평균 객단가**를 형성하고 있습니다. 이는 인플루언서의 팬덤이 상품의 가격보다는 '추천'과 '신뢰'에 기반하여 고가 라인업을 기꺼이 구매함을 의미합니다.
    - **영입 전략**: 따라서 신규 인플루언서 영입 시, 저가형 미끼 상품보다는 **'제주 한정판 프리미엄 세트'**와 같은 고단가 기획 상품을 전면에 내세우는 것이 매출 극대화와 인플루언서의 수익성(수수료) 확보 양면에서 유리합니다.
    """)

    st.markdown("---")
    
    # 7. 향후 추진 전략 (Recruitment)
    st.markdown("### 7. 향후 추진 전략")
    st.info("""
    - **제주 로컬 엠버서더**: 제주 가치를 스토리텔링할 수 있는 인플루언서 상시 영입.
    - **콘텐츠 소스 지원**: SNS용 고퀄리티 브이로그 및 과수원 드론 영상 본사 제공.
    - **신규 수혈 인센티브**: 신규 가입 고객 유치 기여도에 따른 성과급 차등 지급.
    - **한정판 패키지**: 인플루언서 채널 전용 독점 라인업 구성을 통한 경쟁력 강화.
    """)
        
with tab5:
    st.header("🚀 데이터 기반 마케팅 최적화 전략")
    st.markdown("데이터 분석 결과를 바탕으로 매출 증대와 재구매율 향상을 위한 5가지 핵심 전략을 제안합니다.")

    # [추가 차트 1] 그룹별 객단가 비교 및 전략
    st.subheader("1. 그룹별 수익성 강화 (객단가 분석)")
    col_a1, col_a2 = st.columns([2, 1])
    with col_a1:
        group_aov = calculate_true_aov(f_df, '그룹')
        fig_a1 = px.bar(group_aov, x='그룹', y='AOV', color='그룹', 
                         title="그룹별 평균 객단가(AOV) 비교",
                         text_auto='.0f', labels={'AOV': '평균 객단가(원)'})
        st.plotly_chart(fig_a1, use_container_width=True)
    with col_a2:
        st.info("""
        **[분석 결과]**
        - 특정 그룹의 객단가가 높게 나타나는 경우, 해당 그룹의 **세트 상품 구성**이 유효함을 의미합니다.
        **[전략]**
        - 객단가가 낮은 그룹은 '함께 사면 좋은 과일' 추천 기능을 강화하여 결제 단가를 높이는 유도 마케팅이 필요합니다.
        """)

    st.markdown("---")

    # [추가 차트 2] 시간대별 주문 분포 (피크타임 타겟팅)
    st.subheader("2. 시간대별 푸시 마케팅 최적화")
    col_b1, col_b2 = st.columns([2, 1])
    with col_b1:
        f_df['주문시간'] = f_df['주문일'].dt.hour
        hour_dist = f_df.groupby('주문시간').size().reset_index(name='주문건수')
        fig_b1 = px.line(hour_dist, x='주문시간', y='주문건수', markers=True,
                          title="시간대별 주문 발생 현황",
                          labels={'주문시간': '시(Hour)', '주문건수': '주문 수'})
        st.plotly_chart(fig_b1, use_container_width=True)
    with col_b2:
        st.success("""
        **[분석 결과]**
        - 주문이 집중되는 **피크 타임(Peak Time)** 전후 1시간이 마케팅 효율이 가장 높습니다.
        **[전략]**
        - 주문 급증 시간 직전에 카카오톡 알림톡이나 앱 푸시를 발송하여 유입을 극대화하세요.
        """)

    st.markdown("---")

    # [추가 차트 3] 그룹별 재구매 경험 비중 (파이 차트)
    st.subheader("3. 고객 충성도(Loyalty) 강화 전략")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        # 킹댕즈 그룹 재구매 비중
        kd_df = f_df[f_df['그룹'] == '킹댕즈']
        kd_repeat = kd_df['재구매여부'].apply(lambda x: '재구매' if x else '신규').value_counts()
        fig_c1 = px.pie(values=kd_repeat.values, names=kd_repeat.index, hole=0.5,
                         title="킹댕즈 그룹 신규 vs 재구매 비중", color_discrete_sequence=px.colors.sequential.RdBu)
        st.plotly_chart(fig_c1, use_container_width=True)
    with col_c2:
        # 일반 셀러 그룹 재구매 비중
        gen_df = f_df[f_df['그룹'] == '일반 셀러']
        gen_repeat = gen_df['재구매여부'].apply(lambda x: '재구매' if x else '신규').value_counts()
        fig_c2 = px.pie(values=gen_repeat.values, names=gen_repeat.index, hole=0.5,
                         title="일반 셀러 그룹 신규 vs 재구매 비중", color_discrete_sequence=px.colors.sequential.Greens)
        st.plotly_chart(fig_c2, use_container_width=True)
    st.warning("""
    **[전략적 제언]**
    - 재구매 비중이 높은 그룹은 **기존 고객 유지(Retention)** 마케팅(리워드 프로그램 등)에 집중하고, 
    신규 비중이 높은 그룹은 **첫 구매 혜택**을 강화하여 재방문을 유도해야 합니다.
    """)

    st.markdown("---")

    # [추가 차트 4] 지역별 주요 유입 경로 (히트맵)
    st.subheader("4. 지역별 맞춤형 주문 경로 마케팅")
    reg_path = f_df.groupby(['광역지역(정식)', '주문경로']).size().unstack(fill_value=0)
    fig_d1 = px.imshow(reg_path, text_auto=True, color_continuous_scale='Viridis',
                        title="지역별 주문 경로 이용 현황 (건수)",
                        labels=dict(x="주문 경로", y="지역", color="주문 건수"))
    st.plotly_chart(fig_d1, use_container_width=True)
    st.info("""
    **[분석 결과]**
    - 특정 지역에서 특정 경로(예: 카카오톡, 인스타그램)의 유입이 두드러지는 패턴을 보입니다.
    **[전략]**
    - 지역 타겟팅 광고 집행 시, 해당 지역에서 가장 활발한 경로를 최우선 매체로 선정하여 광고 효율을 최적화하세요.
    """)

    st.markdown("---")

    # [추가 차트 5] 품종별 매출 기여도 및 성장 가능성
    st.subheader("5. 전략 품목 선정 (매출 기여도)")
    prod_rev = f_df.groupby('품종')['실결제 금액'].sum().sort_values(ascending=False).head(10).reset_index()
    fig_e1 = px.funnel(prod_rev, x='실결제 금액', y='품종', color='품종',
                        title="주요 품종별 매출 기여도 Top 10")
    st.plotly_chart(fig_e1, use_container_width=True)
    st.success("""
    **[최종 제언]**
    - 매출 비중이 가장 큰 핵심 품목(예: 감귤)은 **안정적 공급망 확보**에 주력하고,
    - 성장 가능성이 높은 서브 품목(예: 황금향, 레드향)은 **연관 상품 추천**을 통해 제2의 핵심 품목으로 육성해야 합니다.
    """)

# --- 탭 6: 전체데이터 ---
with tab6:
    st.subheader("데이터 미리보기")
    st.dataframe(f_df.sort_values(by='주문일', ascending=False).head(100), use_container_width=True)

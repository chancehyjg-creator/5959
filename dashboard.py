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
    repeat_rate = (f_df['재구매 횟수'] > 0).mean() * 100
    st.metric("재구매 비중", f"{repeat_rate:.1f}%")

# ----------------------------------------------------------------
# 3. 탭 구성 (EDA 및 상세 분석)
# ----------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 매출 & 채널", "📊 셀러 & 로열티", "🗺️ 지역별 분석", "🔍 경로 상세분석", "🎯 마케팅 전략", "📋 전체데이터"
])

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
        sel_contri['셀러순위비중'] = (range(1, len(sel_contri)+1) / len(sel_contri)) * 100
        
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
        '재구매 횟수': lambda x: (x > 0).mean() * 100
    }).rename(columns={'실결제 금액': '매출', '주문번호': '건수', '재구매 횟수': '재구매비중(%)'}).reset_index()
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
        repeats = f_df[f_df['재구매 횟수'] > 0].groupby('셀러명').size()
        r_ratio = (repeats / counts * 100).fillna(0).loc[counts[counts>=30].index].nlargest(10).reset_index()
        r_ratio.columns = ['셀러명', '재구매율(%)']
        st.dataframe(r_ratio, use_container_width=True)

# --- 탭 3: 지역별 분석 ---
with tab3:
    st.subheader("🗺️ 지역별 입체 분석 및 전략적 클러스터링")
    st.markdown("전국 지역별 매출 분포와 주문 경로, 셀러 간의 상관관계를 한눈에 파악할 수 있도록 시각화하였습니다.")

    # 1. 시각적 클러스터링: 매출 vs 재구매율 (지역 성격 분류)
    st.subheader("1. 지역별 성격 분류 (매출 규모 vs 재구매 로열티)")
    
    reg_stats = f_df.groupby('광역지역(정식)').agg({
        '실결제 금액': 'sum',
        '재구매 횟수': lambda x: (x > 0).mean() * 100,
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

# --- 탭 4: 경로 상세분석 ---
with tab4:
    st.subheader("기타/크롬 경로 상세 분석 (표 5)")
    detail_paths = f_df[f_df['주문경로'].isin(['기타', '크롬'])]
    
    # [표 5] 신규 vs 기존 유입 분석
    st.write("**신규 유입 고객 vs 기존 고객 재방문 비중**")
    detail_paths['유형'] = detail_paths['재구매 횟수'].apply(lambda x: '신규' if x == 0 else '기존')
    path_summary = detail_paths.groupby(['주문경로', '유형']).size().unstack(fill_value=0)
    st.table(path_summary)

    # [그래프 7] 회원/비회원 구분
    st.write("**회원 vs 비회원 구매 비중**")
    mem_dist = detail_paths.groupby(['주문경로', '회원구분']).size().reset_index(name='건수')
    fig7 = px.bar(mem_dist, x='주문경로', y='건수', color='회원구분', barmode='group')
    st.plotly_chart(fig7, use_container_width=True)

# --- 탭 5: 마케팅 전략 ---
with tab5:
    st.header("🚀 데이터 기반 마케팅 최적화 전략")
    st.markdown("데이터 분석 결과를 바탕으로 매출 증대와 재구매율 향상을 위한 5가지 핵심 전략을 제안합니다.")

    # [추가 차트 1] 그룹별 객단가 비교 및 전략
    st.subheader("1. 그룹별 수익성 강화 (객단가 분석)")
    col_a1, col_a2 = st.columns([2, 1])
    with col_a1:
        group_aov = f_df.groupby('그룹')['실결제 금액'].mean().reset_index()
        fig_a1 = px.bar(group_aov, x='그룹', y='실결제 금액', color='그룹', 
                         title="그룹별 평균 객단가(AOV) 비교",
                         text_auto='.0f', labels={'실결제 금액': '평균 결제액'})
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
        kd_repeat = kd_df['재구매 횟수'].apply(lambda x: '재구매' if x > 0 else '신규').value_counts()
        fig_c1 = px.pie(values=kd_repeat.values, names=kd_repeat.index, hole=0.5,
                         title="킹댕즈 그룹 신규 vs 재구매 비중", color_discrete_sequence=px.colors.sequential.RdBu)
        st.plotly_chart(fig_c1, use_container_width=True)
    with col_c2:
        # 일반 셀러 그룹 재구매 비중
        gen_df = f_df[f_df['그룹'] == '일반 셀러']
        gen_repeat = gen_df['재구매 횟수'].apply(lambda x: '재구매' if x > 0 else '신규').value_counts()
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

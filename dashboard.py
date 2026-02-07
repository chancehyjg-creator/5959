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
    st.subheader("매출 추이 및 채널 기여도 (그래프 1, 2, 3)")
    # [그래프 1] 시계열 매출 추이
    trend = f_df.groupby(['주문날짜', '그룹'])['실결제 금액'].sum().reset_index()
    fig1 = px.line(trend, x='주문날짜', y='실결제 금액', color='그룹', markers=True, title="일일 매출 추이")
    st.plotly_chart(fig1, use_container_width=True)

    # [신규 추가: 그래프 1-2] 일별 활동 셀러 수 추이
    st.subheader("일별 활동 셀러 수 추이")
    active_sellers = f_df.groupby(['주문날짜', '그룹'])['셀러명'].nunique().reset_index(name='셀러수')
    fig1_2 = px.line(active_sellers, x='주문날짜', y='셀러수', color='그룹', markers=True, 
                     title="일자별 실제 주문이 발생한 셀러 수 변화",
                     labels={'주문날짜': '날짜', '셀러수': '활동 셀러 수'})
    st.plotly_chart(fig1_2, use_container_width=True)

    c1, c2 = st.columns([2, 1])
    with c1:
        # [그래프 2] 채널별 매출 비중
        ch_rev = f_df.groupby('주문경로')['실결제 금액'].sum().reset_index()
        fig2 = px.pie(ch_rev, values='실결제 금액', names='주문경로', hole=0.4, title="채널별 매출 비중")
        st.plotly_chart(fig2, use_container_width=True)

    # [그래프 3] 채널별 평균 결제액
    ch_aov = f_df.groupby('주문경로')['실결제 금액'].mean().sort_values(ascending=False).reset_index()
    fig3 = px.bar(ch_aov, x='주문경로', y='실결제 금액', color='주문경로', title="채널별 건당 평균 결제액(AOV)")
    st.plotly_chart(fig3, use_container_width=True)

    # [표 1] 채널 성과 요약
    st.subheader("📝 채널별 성과 요약 (표 1)")
    ch_sum = f_df.groupby('주문경로').agg({'실결제 금액':'sum', '주문번호':'count'}).rename(columns={'실결제 금액':'매출', '주문번호':'건수'}).reset_index()
    st.dataframe(ch_sum.sort_values(by='매출', ascending=False), hide_index=True, use_container_width=True)

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
    st.subheader("지역별 매출 및 연계 분석 (그래프 6, 표 4)")
    # [그래프 6] 지역별 총 매출
    reg_rev = f_df.groupby('광역지역(정식)')['실결제 금액'].sum().sort_values(ascending=False).reset_index()
    fig6 = px.bar(reg_rev, x='광역지역(정식)', y='실결제 금액', color='실결제 금액', title="지역별 매출 규모")
    st.plotly_chart(fig6, use_container_width=True)

    # [표 4] 지역 x 경로 x 셀러 베스트 조합
    st.subheader("📍 지역별 베스트 [경로 x 셀러] 조합")
    sel_reg = st.selectbox("조합을 확인할 지역", options=reg_rev['광역지역(정식)'].tolist())
    reg_df = f_df[f_df['광역지역(정식)'] == sel_reg]
    best_combo = reg_df.groupby(['주문경로', '셀러명'])['실결제 금액'].sum().nlargest(5).reset_index()
    best_combo.columns = ['주문경로', '셀러명', '매출합계']
    st.table(best_combo)

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
    st.header("🚀 재구매율 증대를 위한 전략적 제언")
    
    # 전략 1: 품목 다변화 (Cross-selling)
    st.subheader("1. 교차 판매(Cross-selling) 전략")
    col_st1, col_st2 = st.columns([1, 2])
    with col_st1:
        st.info("""
        **[데이터 인사이트]**
        재구매 고객은 첫 구매 대비 **황금향, 고구마, 한라봉** 구매 비중이 확연히 높습니다.
        **[Action Item]**
        감귤 구매 후 7일 시점에 연관 품목 할인 쿠폰을 발송하세요.
        """)
    with col_st2:
        repeat_products = f_df[f_df['재구매 횟수'] > 0]['품종'].value_counts().head(5).reset_index()
        fig_st1 = px.bar(repeat_products, x='품종', y='count', color='품종', 
                         title="재구매 고객 선호 품종 Top 5")
        st.plotly_chart(fig_st1, use_container_width=True)

    st.markdown("---")
    
    # 전략 2: 채널 로열티
    st.subheader("2. 채널별 타겟팅 전략")
    col_st3, col_st4 = st.columns([2, 1])
    with col_st3:
        ch_total = f_df.groupby('주문경로').size()
        ch_repeat = f_df[f_df['재구매 횟수'] > 0].groupby('주문경로').size()
        ch_loyalty = (ch_repeat / ch_total * 100).fillna(0).reset_index(name='재구매비율')
        fig_st2 = px.bar(ch_loyalty.sort_values(by='재구매비율', ascending=False), 
                         x='주문경로', y='재구매비율', color='재구매비율',
                         title="채널별 재구매 기여도(%)")
        st.plotly_chart(fig_st2, use_container_width=True)
    with col_st4:
        st.success("""
        **[핵심 전략]**
        - **카카오톡**: 경기도 지역 타겟 메시지 집중
        - **크롬**: 브랜드 키워드 검색 광고 강화
        - **인스타그램**: 세트 상품(감귤+황금향) 홍보
        """)

# --- 탭 6: 전체데이터 ---
with tab6:
    st.subheader("데이터 미리보기")
    st.dataframe(f_df.sort_values(by='주문일', ascending=False).head(100), use_container_width=True)

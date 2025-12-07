import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import google.generativeai as genai
import json
import os
import time

# 1. 페이지 설정
st.set_page_config(page_title="Literary Nexus", layout="wide")

# 2. 한글 폰트 설정
font_path = 'NanumGothic.ttf'
font_name = 'sans-serif'
try:
    if os.path.exists(font_path):
        font_prop = fm.FontProperties(fname=font_path)
        font_name = font_prop.get_name()
        plt.rc('font', family=font_name)
        plt.rcParams['axes.unicode_minus'] = False
except Exception:
    pass

# 3. 제목 및 설명
st.title("📚 AI 기반 도서 추천 네트워크")
st.markdown("세 권의 책을 입력하면, 취향을 분석하여 새로운 책들을 연결해 드립니다.")

# 4. API 키 설정 (구 SDK 방식)
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=GOOGLE_API_KEY)
except Exception as e:
    st.error(f"API 키 설정 오류: {e}")

# 5. 사이드바 입력창
with st.sidebar:
    st.header("나의 인생 책 3권")
    book1 = st.text_input("첫 번째 책", placeholder="예: 데미안")
    book2 = st.text_input("두 번째 책", placeholder="예: 총, 균, 쇠")
    book3 = st.text_input("세 번째 책", placeholder="예: 1984")
    analyze_btn = st.button("네트워크 생성하기")

# 6. 사용 가능한 모델 확인 함수
@st.cache_data(ttl=3600)
def get_available_models():
    """사용 가능한 Gemini 모델 목록 조회"""
    try:
        models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                models.append(m.name)
        return models
    except Exception as e:
        st.error(f"모델 목록 조회 오류: {e}")
        return []

# 7. 그래프 생성 로직 (구 SDK + 자동 모델 선택)
def create_graph(books):
    prompt = f"""
    다음 3권의 책을 기반으로 도서 추천 네트워크를 만들어줘: {books}
    
    [조건]
    1. 입력된 3권의 책 각각에 대해, 문체/난이도/철학이 유사한 연관 도서를 2~3권씩 추천해줘.
    2. 추천된 책들끼리도 연관성이 있다면 연결해줘.
    3. 결과는 반드시 오직 JSON 형식으로만 출력해. 다른 말은 하지 마.
    
    [JSON 형식 예시]
    {{
        "nodes": [
            {{"id": "책제목1", "group": 1}},
            {{"id": "책제목2", "group": 2}}
        ],
        "edges": [
            {{"source": "책제목1", "target": "책제목2", "label": "유사한 허무주의"}}
        ]
    }}
    """
    
    # 시도할 모델 우선순위 목록
    model_priority = [
        'models/gemini-1.5-flash-latest',
        'models/gemini-1.5-flash',
        'models/gemini-1.5-pro-latest',
        'models/gemini-1.5-pro',
        'models/gemini-pro'
    ]
    
    # 사용 가능한 모델 확인
    available_models = get_available_models()
    
    # 우선순위에 따라 사용 가능한 모델 찾기
    selected_model = None
    for model_name in model_priority:
        if model_name in available_models:
            selected_model = model_name
            break
    
    if not selected_model:
        st.error(f"사용 가능한 모델이 없습니다. 사용 가능한 모델: {available_models}")
        return None
    
    st.info(f"🤖 사용 중인 모델: {selected_model}")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            model = genai.GenerativeModel(selected_model)
            response = model.generate_content(prompt)
            text = response.text.replace("```json", "").replace("```", "")
            return json.loads(text)
        except Exception as e:
            error_str = str(e)
            
            # 429 Rate Limit 에러 처리
            if '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str:
                if attempt < max_retries - 1:
                    wait_time = 10 * (attempt + 1)
                    st.warning(f"⏳ 할당량 초과. {wait_time}초 후 재시도합니다... (시도 {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    st.error("⚠️ API 무료 할당량을 초과했습니다. 1~2분 후 다시 시도해주세요.")
                    st.info("💡 팁: 새 API 키를 생성하거나, 몇 분 후 다시 시도해보세요.")
                    return None
            
            # 404 모델 없음 에러 처리
            elif '404' in error_str or 'NOT_FOUND' in error_str:
                st.error(f"❌ 모델을 찾을 수 없습니다: {selected_model}")
                st.info(f"사용 가능한 모델: {', '.join(available_models)}")
                return None
            
            else:
                st.error(f"AI 응답 오류: {e}")
                return None
    
    return None

# 8. 메인 실행 및 시각화
if analyze_btn and book1 and book2 and book3:
    with st.spinner("AI가 책들의 관계를 분석하고 있습니다..."):
        data = create_graph([book1, book2, book3])
        
        if data:
            G = nx.Graph()
            for node in data.get('nodes', []):
                G.add_node(node['id'], group=node.get('group', 1))
            for edge in data.get('edges', []):
                G.add_edge(edge['source'], edge['target'], label=edge.get('label', ''))
            
            plt.figure(figsize=(12, 8))
            pos = nx.spring_layout(G, k=0.8)
            
            nx.draw_networkx_nodes(G, pos, node_size=2500, node_color='skyblue', alpha=0.9)
            nx.draw_networkx_labels(G, pos, font_family=font_name, font_size=10)
            nx.draw_networkx_edges(G, pos, width=1.5, alpha=0.5, edge_color='gray')
            
            st.pyplot(plt)
            st.success("✅ 완료되었습니다!")

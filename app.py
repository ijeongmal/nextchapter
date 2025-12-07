import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import google.generativeai as genai
import json
import os

# 1. 페이지 설정
st.set_page_config(page_title="Literary Nexus", layout="wide")

# 2. 한글 폰트 설정 (안전장치 포함)
font_path = 'NanumGothic.ttf'
font_name = 'sans-serif' # 폰트 없을 시 기본값

try:
    if os.path.exists(font_path):
        font_prop = fm.FontProperties(fname=font_path)
        font_name = font_prop.get_name()
        plt.rc('font', family=font_name)
        plt.rcParams['axes.unicode_minus'] = False
    else:
        # 폰트 파일이 없어도 에러 내지 말고 넘어감
        pass 
except Exception:
    pass

# 3. 제목 및 설명
st.title("📚 AI 기반 도서 추천 네트워크")
st.markdown("세 권의 책을 입력하면, 취향을 분석하여 새로운 책들을 연결해 드립니다.")

# 4. API 키 설정
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=GOOGLE_API_KEY)
except Exception:
    st.error("API 키가 설정되지 않았습니다.")

# 5. 사이드바 입력창
with st.sidebar:
    st.header("나의 인생 책 3권")
    book1 = st.text_input("첫 번째 책", placeholder="예: 데미안")
    book2 = st.text_input("두 번째 책", placeholder="예: 총, 균, 쇠")
    book3 = st.text_input("세 번째 책", placeholder="예: 1984")
    analyze_btn = st.button("네트워크 생성하기")

# 6. 그래프 생성 로직
def create_graph(books):
    # 🌟 [핵심 수정] 가장 안정적인 'gemini-pro' 모델 사용
    model = genai.GenerativeModel('gemini-pro')
    
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
    
    try:
        response = model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "")
        return json.loads(text)
    except Exception as e:
        st.error(f"AI 응답 오류: {e}")
        return None

# 7. 메인 실행 및 시각화
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
            
            # 폰트 적용하여 그리기
            nx.draw_networkx_nodes(G, pos, node_size=2500, node_color='skyblue', alpha=0.9)
            nx.draw_networkx_labels(G, pos, font_family=font_name, font_size=10)
            nx.draw_networkx_edges(G, pos, width=1.5, alpha=0.5, edge_color='gray')
            
            st.pyplot(plt)
            st.success("완료되었습니다!")
